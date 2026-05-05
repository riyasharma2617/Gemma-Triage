package com.gemma.triage

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.gemma.triage.inference.TriageCode
import com.gemma.triage.inference.TriageResult
import com.gemma.triage.viewmodel.TriageUiState
import com.gemma.triage.viewmodel.TriageViewModel
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private val viewModel: TriageViewModel by viewModels()

    private lateinit var tvStatus: TextView
    private lateinit var cardResult: LinearLayout
    private lateinit var tvTriageCode: TextView
    private lateinit var tvConfidence: TextView
    private lateinit var tvReasoning: TextView
    private lateinit var tvSteps: TextView
    private lateinit var scrollConversation: ScrollView
    private lateinit var tvConversation: TextView
    private lateinit var tvSpeaking: TextView
    private lateinit var tvPatientCount: TextView
    private lateinit var btnStartTriage: Button
    private lateinit var btnNextPatient: Button

    private val conversationLog = StringBuilder()

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { grants ->
        if (grants[Manifest.permission.RECORD_AUDIO] == true) {
            viewModel.startListening()
        } else {
            tvStatus.text = "Microphone permission required"
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        tvStatus = findViewById(R.id.tvStatus)
        cardResult = findViewById(R.id.cardResult)
        tvTriageCode = findViewById(R.id.tvTriageCode)
        tvConfidence = findViewById(R.id.tvConfidence)
        tvReasoning = findViewById(R.id.tvReasoning)
        tvSteps = findViewById(R.id.tvSteps)
        scrollConversation = findViewById(R.id.scrollConversation)
        tvConversation = findViewById(R.id.tvConversation)
        tvSpeaking = findViewById(R.id.tvSpeaking)
        tvPatientCount = findViewById(R.id.tvPatientCount)
        btnStartTriage = findViewById(R.id.btnStartTriage)
        btnNextPatient = findViewById(R.id.btnNextPatient)

        btnStartTriage.setOnClickListener { onStartTriageClicked() }
        btnNextPatient.setOnClickListener { viewModel.resetToNextPatient() }

        observeViewModel()
    }

    private fun observeViewModel() {
        lifecycleScope.launch {
            viewModel.uiState.collect { state -> renderState(state) }
        }
        lifecycleScope.launch {
            viewModel.patientCount.collect { count ->
                tvPatientCount.text = "Patients triaged: $count"
            }
        }
        lifecycleScope.launch {
            viewModel.modelReady.collect { ready ->
                btnStartTriage.isEnabled = ready
                if (!ready) tvStatus.text = getString(R.string.status_model_loading)
            }
        }
    }

    private fun renderState(state: TriageUiState) {
        when (state) {
            is TriageUiState.Idle -> {
                tvStatus.text = getString(R.string.status_idle)
                cardResult.visibility = View.INVISIBLE
                scrollConversation.visibility = View.GONE
                tvSpeaking.visibility = View.GONE
                btnNextPatient.visibility = View.GONE
                btnStartTriage.isEnabled = viewModel.modelReady.value
            }
            is TriageUiState.Listening -> {
                tvStatus.text = getString(R.string.status_listening)
                btnStartTriage.isEnabled = false
            }
            is TriageUiState.Transcribing -> {
                tvStatus.text = "Heard: ${state.text}"
            }
            is TriageUiState.Analyzing -> {
                tvStatus.text = getString(R.string.status_analyzing)
            }
            is TriageUiState.ResultReady -> {
                showResult(state.result)
                conversationLog.clear()
                scrollConversation.visibility = View.GONE
                btnNextPatient.visibility = View.VISIBLE
            }
            is TriageUiState.Speaking -> {
                tvStatus.text = getString(R.string.status_speaking)
                tvSpeaking.visibility = View.VISIBLE
                tvSpeaking.text = "Speaking: ${state.stage}"
            }
            is TriageUiState.FollowUpListening -> {
                tvStatus.text = getString(R.string.status_follow_up)
                tvSpeaking.visibility = View.GONE
                scrollConversation.visibility = View.VISIBLE
            }
            is TriageUiState.FollowUpAnalyzing -> {
                tvStatus.text = getString(R.string.status_analyzing)
            }
            is TriageUiState.FollowUpSpeaking -> {
                tvSpeaking.visibility = View.VISIBLE
                tvSpeaking.text = "Speaking answer…"
                conversationLog.append("\nQ: ${state.question}\nA: ${state.answer}\n")
                tvConversation.text = conversationLog.toString()
                scrollConversation.post { scrollConversation.fullScroll(View.FOCUS_DOWN) }
            }
            is TriageUiState.Error -> {
                tvStatus.text = "Error: ${state.message}"
                tvSpeaking.visibility = View.GONE
                btnStartTriage.isEnabled = viewModel.modelReady.value
            }
        }
    }

    private fun showResult(result: TriageResult) {
        cardResult.visibility = View.VISIBLE
        tvTriageCode.text = result.triageCode.name
        tvTriageCode.setTextColor(colorForCode(result.triageCode))
        tvConfidence.text = "${(result.confidence * 100).toInt()}% confidence"
        tvReasoning.text = result.reasoning
        tvSteps.text = result.immediateSteps.mapIndexed { i, s -> "${i + 1}. $s" }.joinToString("\n")
    }

    private fun colorForCode(code: TriageCode): Int = when (code) {
        TriageCode.RED -> getColor(R.color.triage_red)
        TriageCode.YELLOW -> getColor(R.color.triage_yellow)
        TriageCode.GREEN -> getColor(R.color.triage_green)
        TriageCode.BLACK -> getColor(R.color.triage_black)
        TriageCode.UNKNOWN -> getColor(R.color.triage_unknown)
    }

    private fun onStartTriageClicked() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            == PackageManager.PERMISSION_GRANTED
        ) {
            viewModel.startListening()
        } else {
            permissionLauncher.launch(
                arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.SEND_SMS)
            )
        }
    }
}
