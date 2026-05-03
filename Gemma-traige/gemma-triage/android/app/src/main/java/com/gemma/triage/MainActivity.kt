package com.gemma.triage

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.gemma.triage.inference.GemmaInferenceEngine

class MainActivity : AppCompatActivity() {

    private lateinit var inferenceEngine: GemmaInferenceEngine

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        inferenceEngine = GemmaInferenceEngine()
        
        // In a real app, you would load the model from assets and bind the UI here
        // launch {
        //     inferenceEngine.loadModel("gemma_2b_quantized.pte")
        // }
    }
}
