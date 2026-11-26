package com.ysn4irix.tpb

import android.app.Application
import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStore
import com.ysn4irix.tpb.data.local.TpbPreferencesRepository
import com.ysn4irix.tpb.data.remote.ApibayApiClient

private val Context.tpbDataStore: DataStore<Preferences> by preferencesDataStore(name = "tpb_prefs")

class TpbApplication : Application() {
    lateinit var preferencesRepository: TpbPreferencesRepository
        private set

    lateinit var apiClient: ApibayApiClient
        private set

    override fun onCreate() {
        super.onCreate()
        preferencesRepository = TpbPreferencesRepository(applicationContext.tpbDataStore)
        apiClient = ApibayApiClient()
    }
}
