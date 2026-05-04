package com.gemma.triage.audio

import kotlin.math.sqrt

/**
 * Basic Voice Activity Detection (VAD) implementation.
 * In a production app, this would use Silero VAD or WebRTC VAD.
 */
class VADDetector {
    
    private val energyThreshold = 1000.0 // Placeholder threshold for audio energy
    
    /**
     * Analyzes an audio frame to determine if it contains speech.
     * @param audioFrame The 16-bit PCM audio frame.
     * @return true if speech is detected, false otherwise.
     */
    fun hasSpeech(audioFrame: ByteArray): Boolean {
        if (audioFrame.isEmpty()) return false
        
        var sumEnergy = 0.0
        // Convert ByteArray back to short array for energy calculation
        for (i in audioFrame.indices step 2) {
            if (i + 1 < audioFrame.size) {
                val sample = (audioFrame[i].toInt() and 0xFF) or (audioFrame[i + 1].toInt() shl 8)
                sumEnergy += sample * sample
            }
        }
        
        val rmsEnergy = sqrt(sumEnergy / (audioFrame.size / 2))
        return rmsEnergy > energyThreshold
    }
}
