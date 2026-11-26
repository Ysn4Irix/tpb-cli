package com.ysn4irix.tpb.data.remote

import com.ysn4irix.tpb.domain.model.SearchMode
import com.ysn4irix.tpb.domain.model.Torrent
import com.ysn4irix.tpb.domain.model.TorrentFile
import com.ysn4irix.tpb.domain.parser.TitleParser
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import okhttp3.Call
import okhttp3.Callback
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import java.io.IOException
import java.net.Proxy
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class ApibayException(message: String, cause: Throwable? = null) : Exception(message, cause)

class ApibayConnectionException(message: String, cause: Throwable? = null) :
    Exception(message, cause)

class ApibayApiClient(
    initialBaseUrl: String = DEFAULT_BASE_URL,
    initialProxyUrl: String? = null,
    private val timeoutSeconds: Long = 15L,
) {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    @Volatile
    var baseUrl: String = NetworkValidator.validateHttpUrl(initialBaseUrl)
        private set

    @Volatile
    var proxyUrl: String? = NetworkValidator.validateProxyUrl(initialProxyUrl)?.normalizedUrl
        private set

    @Volatile
    private var httpClient: OkHttpClient = buildHttpClient(
        NetworkValidator.validateProxyUrl(initialProxyUrl),
    )

    private val searchCache = ConcurrentHashMap<Pair<String, String>, List<Torrent>>()
    private val filesCache = ConcurrentHashMap<String, List<TorrentFile>>()

    fun reconfigure(newBaseUrl: String, newProxyUrl: String?) {
        val validatedUrl = NetworkValidator.validateHttpUrl(newBaseUrl)
        val validatedProxy = NetworkValidator.validateProxyUrl(newProxyUrl)
        baseUrl = validatedUrl
        proxyUrl = validatedProxy?.normalizedUrl
        httpClient = buildHttpClient(validatedProxy)
        clearCache()
    }

    fun clearCache() {
        searchCache.clear()
        filesCache.clear()
    }

    private fun buildHttpClient(proxyConfig: ProxyConfig?): OkHttpClient =
        OkHttpClient.Builder()
            .connectTimeout(timeoutSeconds, TimeUnit.SECONDS)
            .readTimeout(timeoutSeconds, TimeUnit.SECONDS)
            .writeTimeout(timeoutSeconds, TimeUnit.SECONDS)
            .followRedirects(true)
            .proxy(proxyConfig?.toJavaProxy() ?: Proxy.NO_PROXY)
            .build()

    suspend fun searchWithFallback(
        query: String,
        mode: SearchMode,
        useCache: Boolean = true,
    ): List<Torrent> {
        val primary = when (mode) {
            SearchMode.TV -> search(query, category = SearchMode.TV.categoryCode, useCache = useCache)
            SearchMode.MOVIE -> search(query, category = SearchMode.MOVIE.categoryCode, useCache = useCache)
            SearchMode.GENERAL -> search(query, category = SearchMode.GENERAL.categoryCode, useCache = useCache)
        }
        if (primary.isNotEmpty() || mode == SearchMode.GENERAL) {
            return primary
        }
        return search(query, category = SearchMode.GENERAL.categoryCode, useCache = useCache)
    }

    suspend fun search(
        query: String,
        category: String? = null,
        useCache: Boolean = true,
    ): List<Torrent> {
        val cleanQuery = query.trim()
        if (cleanQuery.isEmpty()) return emptyList()

        val catKey = category.orEmpty()
        val cacheKey = cleanQuery.lowercase() to catKey
        if (useCache) {
            searchCache[cacheKey]?.let { return it.toList() }
        }

        val urlBuilder = "$baseUrl/q.php".toHttpUrl().newBuilder()
            .addQueryParameter("q", cleanQuery)
        if (!category.isNullOrEmpty()) {
            urlBuilder.addQueryParameter("cat", category)
        }

        val bodyText = executeGet(urlBuilder.build().toString())
        val parsed = withContext(Dispatchers.Default) {
            parseSearchJson(bodyText)
        }

        searchCache[cacheKey] = parsed
        return parsed.toList()
    }

    suspend fun getParsedFiles(torrentId: String, useCache: Boolean = true): List<TorrentFile> {
        val cleanId = torrentId.trim()
        if (cleanId.isEmpty() || cleanId == "0") return emptyList()

        if (useCache) {
            filesCache[cleanId]?.let { return it.toList() }
        }

        val url = "$baseUrl/f.php".toHttpUrl().newBuilder()
            .addQueryParameter("id", cleanId)
            .build()
            .toString()

        val bodyText = executeGet(url)
        val parsed = withContext(Dispatchers.Default) {
            parseFilesJson(bodyText)
        }

        filesCache[cleanId] = parsed
        return parsed.toList()
    }

    private suspend fun executeGet(url: String): String {
        val request = Request.Builder()
            .url(url)
            .header("User-Agent", DEFAULT_USER_AGENT)
            .header("Accept", "application/json, text/plain, */*")
            .get()
            .build()

        val call = httpClient.newCall(request)
        return try {
            val response = call.await()
            response.use { res ->
                if (!res.isSuccessful) {
                    throw ApibayException("Apibay returned HTTP status ${res.code}")
                }
                res.body?.string() ?: throw ApibayException("Empty response body from Apibay.")
            }
        } catch (ce: CancellationException) {
            throw ce
        } catch (ioe: IOException) {
            throw ApibayConnectionException(
                "Could not connect to $baseUrl: ${ioe.message ?: "network error"}",
                ioe,
            )
        }
    }

    internal fun parseSearchJson(rawBody: String): List<Torrent> {
        val root = runCatching { json.parseToJsonElement(rawBody) }
            .getOrElse { exc ->
                throw ApibayException("Failed to parse JSON response from Apibay: ${exc.message}", exc)
            }
        val array = root as? JsonArray ?: return emptyList()
        if (array.isEmpty()) return emptyList()

        if (array.size == 1) {
            val first = array[0] as? JsonObject
            val id = first?.stringField("id")
            val name = first?.stringField("name")
            if (id == "0" || name == "No results returned") {
                return emptyList()
            }
        }

        val results = mutableListOf<Torrent>()
        for (element in array) {
            val obj = element as? JsonObject ?: continue
            val name = obj.stringField("name").trim()
            val infoHash = obj.stringField("info_hash").trim()
            if (name.isEmpty()) continue
            val torrent = Torrent(
                id = obj.stringField("id"),
                name = name,
                infoHash = infoHash,
                leechers = obj.longField("leechers").toInt(),
                seeders = obj.longField("seeders").toInt(),
                sizeBytes = obj.longField("size"),
                username = obj.stringField("username"),
                added = obj.longField("added"),
                status = obj.stringField("status", default = "member"),
                category = obj.stringField("category", default = "0"),
                imdb = obj.stringField("imdb"),
            )
            results.add(TitleParser.enrichTorrent(torrent))
        }
        return results.sortedByDescending { it.seeders }
    }

    internal fun parseFilesJson(rawBody: String): List<TorrentFile> {
        val root = runCatching { json.parseToJsonElement(rawBody) }
            .getOrElse { exc ->
                throw ApibayException("Failed to parse file list response: ${exc.message}", exc)
            }
        val array = root as? JsonArray ?: return emptyList()
        val files = mutableListOf<TorrentFile>()

        for (element in array) {
            val obj = element as? JsonObject ?: continue
            val rawName = obj["name"]
            val name = when (rawName) {
                is JsonArray -> rawName
                    .mapNotNull { (it as? JsonPrimitive)?.contentOrNull }
                    .joinToString("/")
                is JsonPrimitive -> rawName.contentOrNull.orEmpty()
                else -> ""
            }.trim()

            if (name.isEmpty() || name.equals("File list not found", ignoreCase = true)) {
                continue
            }

            val rawSize = obj["size"]
            val sizeValue = when (rawSize) {
                is JsonArray -> (rawSize.firstOrNull() as? JsonPrimitive)?.contentOrNull
                is JsonPrimitive -> rawSize.contentOrNull
                else -> null
            }?.toLongOrNull()?.coerceAtLeast(0L) ?: 0L

            files.add(TorrentFile(name = name, sizeBytes = sizeValue))
        }

        return files
    }

    private fun JsonObject.stringField(key: String, default: String = ""): String =
        (this[key] as? JsonPrimitive)?.contentOrNull ?: default

    private fun JsonObject.longField(key: String): Long =
        (this[key] as? JsonPrimitive)?.contentOrNull?.toLongOrNull() ?: 0L

    private suspend fun Call.await(): Response = suspendCancellableCoroutine { cont ->
        cont.invokeOnCancellation { cancel() }
        enqueue(
            object : Callback {
                override fun onFailure(call: Call, e: IOException) {
                    if (!cont.isCancelled) {
                        cont.resumeWithException(e)
                    }
                }

                override fun onResponse(call: Call, response: Response) {
                    if (cont.isCancelled) {
                        response.close()
                        return
                    }
                    cont.resume(response)
                }
            },
        )
    }

    companion object {
        const val DEFAULT_BASE_URL = "https://apibay.org"
        private const val DEFAULT_USER_AGENT =
            "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
    }
}
