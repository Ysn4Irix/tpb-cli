package com.ysn4irix.tpb.data.remote

import java.net.InetSocketAddress
import java.net.Proxy
import java.net.URI
import java.util.Locale

data class ProxyConfig(
    val normalizedUrl: String,
    val type: Proxy.Type,
    val host: String,
    val port: Int,
) {
    fun toJavaProxy(): Proxy =
        Proxy(type, InetSocketAddress.createUnresolved(host, port))
}

object NetworkValidator {
    fun validateHttpUrl(rawUrl: String): String {
        val cleaned = rawUrl.trim().trimEnd('/')
        val uri = runCatching { URI(cleaned) }.getOrNull()
            ?: throw IllegalArgumentException("API URL is malformed.")
        val scheme = uri.scheme?.lowercase(Locale.US).orEmpty()
        val host = uri.host.orEmpty()
        if (scheme !in setOf("http", "https") || host.isBlank()) {
            throw IllegalArgumentException(
                "API URL must start with http:// or https:// and include a hostname.",
            )
        }
        return cleaned
    }

    fun isCleartextHttp(url: String): Boolean =
        url.trim().lowercase(Locale.US).startsWith("http://")

    fun validateProxyUrl(rawProxy: String?): ProxyConfig? {
        val cleaned = rawProxy?.trim().orEmpty()
        if (cleaned.isEmpty()) return null

        val uri = runCatching { URI(cleaned) }.getOrNull()
            ?: throw IllegalArgumentException("Proxy URL is malformed.")
        val scheme = uri.scheme?.lowercase(Locale.US).orEmpty()
        val host = uri.host.orEmpty()
        if (scheme !in setOf("http", "https", "socks5", "socks5h") || host.isBlank()) {
            throw IllegalArgumentException(
                "Proxy URL must use http://, https://, socks5://, or socks5h:// and include a host.",
            )
        }

        val proxyType = when (scheme) {
            "socks5", "socks5h" -> Proxy.Type.SOCKS
            else -> Proxy.Type.HTTP
        }
        val port = when {
            uri.port > 0 -> uri.port
            uri.port == -1 && proxyType == Proxy.Type.SOCKS -> 9050
            uri.port == -1 -> 8080
            else -> -1
        }
        if (port !in 1..65535) {
            throw IllegalArgumentException("Proxy port must be between 1 and 65535.")
        }

        return ProxyConfig(
            normalizedUrl = cleaned,
            type = proxyType,
            host = host,
            port = port,
        )
    }
}
