package com.gemma.triage

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import com.gemma.triage.inference.TriageCode
import com.gemma.triage.inference.TriageResult
import com.gemma.triage.viewmodel.TriageUiState
import com.gemma.triage.viewmodel.TriageViewModel
import kotlinx.coroutines.launch

class TriageFragment : Fragment() {

    private val viewModel: TriageViewModel by activityViewModels()

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

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View =
        inflater.inflate(R.layout.fragment_triage, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        tvStatus = view.findViewById(R.id.tvStatus)
        cardResult = view.findViewById(R.id.cardResult)
        tvTriageCode = view.findViewById(R.id.tvTriageCode)
        tvConfidence = view.findViewById(R.id.tvConfidence)
        tvReasoning = view.findViewById(R.id.tvReasoning)
        tvSteps = view.findViewById(R.id.tvSteps)
        scrollConversation = view.findViewById(R.id.scrollConversation)
        tvConversation = view.findViewById(R.id.tvConversation)
        tvSpeaking = view.findViewById(R.id.tvSpeaking)
        tvPatientCount = view.findViewById(R.id.tvPatientCount)
        btnStartTriage = view.findViewById(R.id.btnStartTriage)
        btnNextPatient = view.findViewById(R.id.btnNextPatient)

        btnStartTriage.setOnClickListener { onStartTriageClicked() }
        btnNextPatient.setOnClickListener { viewModel.resetToNextPatient() }

        observeViewModel()
    }

    private fun observeViewModel() {
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.uiState.collect { state -> renderState(state) }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.patientCount.collect { count ->
                tvPatientCount.text = "Patients triaged: $count"
            }
        }
        viewLifecycleOwner.lifecycleScope.launch {
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
        TriageCode.RED -> requireContext().getColor(R.color.triage_red)
        TriageCode.YELLOW -> requireContext().getColor(R.color.triage_yellow)
        TriageCode.GREEN -> requireContext().getColor(R.color.triage_green)
        TriageCode.BLACK -> requireContext().getColor(R.color.triage_black)
        TriageCode.UNKNOWN -> requireContext().getColor(R.color.triage_unknown)
    }

    private fun onStartTriageClicked() {
        if (ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.RECORD_AUDIO)
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
