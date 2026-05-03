package com.gemma.triage.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn

class AudioCaptureManager {

    private var audioRecord: AudioRecord? = null
    private val sampleRate = 16000 // 16kHz for speech models
    private val channelConfig = AudioFormat.CHANNEL_IN_MONO
    private val audioFormat = AudioFormat.ENCODING_PCM_16BIT
    private val minBufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat)
    private var isRecording = false

    @SuppressLint("MissingPermission") // Permissions handled at UI level
    fun startRecording(): Flow<ByteArray> = flow {
        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate,
            channelConfig,
            audioFormat,
            minBufferSize * 2
        )

        audioRecord?.startRecording()
        isRecording = true

        val buffer = ByteArray(minBufferSize)
        while (isRecording) {
            val readSize = audioRecord?.read(buffer, 0, buffer.size) ?: 0
            if (readSize > 0) {
                emit(buffer.copyOf(readSize))
            }
        }
    }.flowOn(Dispatchers.IO)

    fun stopRecording() {
        isRecording = false
        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null
    }
}
