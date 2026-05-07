package com.gemma.triage

import android.Manifest
import android.animation.AnimatorSet
import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.animation.DecelerateInterpolator
import android.view.animation.OvershootInterpolator
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.card.MaterialCardView
import com.google.android.material.button.MaterialButton
import com.google.android.material.floatingactionbutton.ExtendedFloatingActionButton
import com.google.android.material.progressindicator.LinearProgressIndicator
import com.gemma.triage.inference.TriageCode
import com.gemma.triage.inference.TriageResult
import com.gemma.triage.viewmodel.TriageUiState
import com.gemma.triage.viewmodel.TriageViewModel
import kotlinx.coroutines.launch

class TriageFragment : Fragment() {

    private val viewModel: TriageViewModel by activityViewModels()

    private lateinit var progressIndicator: LinearProgressIndicator
    private lateinit var tvStatus: TextView
    private lateinit var cardResult: MaterialCardView
    private lateinit var tvTriageCode: TextView
    private lateinit var tvConfidence: TextView
    private lateinit var tvReasoning: TextView
    private lateinit var tvSteps: TextView
    private lateinit var rvConversation: RecyclerView
    private lateinit var tvSpeaking: TextView
    private lateinit var tvPatientCount: TextView
    private lateinit var btnNextPatient: MaterialButton
    private lateinit var fabMic: ExtendedFloatingActionButton
    private lateinit var viewPulse: View

    private val bubbleAdapter = ConversationBubbleAdapter()
    private val conversationBubbles = mutableListOf<ConversationBubble>()
    private var pulseAnimator: AnimatorSet? = null

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

        progressIndicator = view.findViewById(R.id.progressIndicator)
        tvStatus = view.findViewById(R.id.tvStatus)
        cardResult = view.findViewById(R.id.cardResult)
        tvTriageCode = view.findViewById(R.id.tvTriageCode)
        tvConfidence = view.findViewById(R.id.tvConfidence)
        tvReasoning = view.findViewById(R.id.tvReasoning)
        tvSteps = view.findViewById(R.id.tvSteps)
        rvConversation = view.findViewById(R.id.rvConversation)
        tvSpeaking = view.findViewById(R.id.tvSpeaking)
        tvPatientCount = view.findViewById(R.id.tvPatientCount)
        btnNextPatient = view.findViewById(R.id.btnNextPatient)
        fabMic = view.findViewById(R.id.fabMic)
        viewPulse = view.findViewById(R.id.viewPulse)

        rvConversation.layoutManager = LinearLayoutManager(requireContext()).also { it.stackFromEnd = true }
        rvConversation.adapter = bubbleAdapter

        fabMic.setOnClickListener { onMicClicked() }
        btnNextPatient.setOnClickListener {
            slideOutNextPatient()
            viewModel.resetToNextPatient()
        }

        observeViewModel()
    }

    private fun observeViewModel() {
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.uiState.collect { renderState(it) }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.patientCount.collect { count ->
                tvPatientCount.text = getString(R.string.label_patients_triaged, count)
            }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.modelReady.collect { ready ->
                fabMic.isEnabled = ready
                if (!ready) tvStatus.text = getString(R.string.status_model_loading)
            }
        }
    }

    private fun renderState(state: TriageUiState) {
        when (state) {
            is TriageUiState.Idle -> {
                progressIndicator.visibility = View.INVISIBLE
                tvStatus.text = getString(R.string.status_idle)
                cardResult.visibility = View.INVISIBLE
                rvConversation.visibility = View.GONE
                tvSpeaking.visibility = View.GONE
                slideOutNextPatient()
                stopPulse()
                fabMic.text = getString(R.string.btn_start_triage)
                fabMic.isEnabled = viewModel.modelReady.value
            }
            is TriageUiState.Listening -> {
                progressIndicator.visibility = View.INVISIBLE
                tvStatus.text = getString(R.string.status_listening)
                fabMic.text = getString(R.string.status_listening)
                fabMic.isEnabled = false
                startPulse()
            }
            is TriageUiState.Transcribing -> {
                stopPulse()
                tvStatus.text = "Heard: ${state.text}"
                progressIndicator.visibility = View.VISIBLE
            }
            is TriageUiState.Analyzing -> {
                progressIndicator.visibility = View.VISIBLE
                tvStatus.text = getString(R.string.status_analyzing)
                fabMic.text = getString(R.string.status_analyzing)
            }
            is TriageUiState.ResultReady -> {
                progressIndicator.visibility = View.INVISIBLE
                showResult(state.result)
                conversationBubbles.clear()
                bubbleAdapter.submitList(emptyList())
                rvConversation.visibility = View.GONE
                slideInNextPatient()
                fabMic.text = getString(R.string.btn_start_triage)
                fabMic.isEnabled = false
            }
            is TriageUiState.Speaking -> {
                tvStatus.text = getString(R.string.status_speaking)
                tvSpeaking.visibility = View.VISIBLE
                tvSpeaking.text = "Speaking: ${state.stage}"
                fabMic.text = "Speaking…"
            }
            is TriageUiState.FollowUpListening -> {
                progressIndicator.visibility = View.INVISIBLE
                tvStatus.text = getString(R.string.status_follow_up)
                tvSpeaking.visibility = View.GONE
                rvConversation.visibility = View.VISIBLE
                fabMic.text = "Ask a question…"
                startPulse()
            }
            is TriageUiState.FollowUpAnalyzing -> {
                stopPulse()
                progressIndicator.visibility = View.VISIBLE
                tvStatus.text = getString(R.string.status_analyzing)
            }
            is TriageUiState.FollowUpSpeaking -> {
                progressIndicator.visibility = View.INVISIBLE
                tvSpeaking.visibility = View.VISIBLE
                tvSpeaking.text = "Speaking answer…"
                conversationBubbles.add(ConversationBubble(state.question, isQuestion = true))
                conversationBubbles.add(ConversationBubble(state.answer, isQuestion = false))
                bubbleAdapter.submitList(conversationBubbles.toList())
                rvConversation.scrollToPosition(bubbleAdapter.itemCount - 1)
            }
            is TriageUiState.Error -> {
                progressIndicator.visibility = View.INVISIBLE
                stopPulse()
                tvStatus.text = "Error: ${state.message}"
                tvSpeaking.visibility = View.GONE
                fabMic.text = getString(R.string.btn_start_triage)
                fabMic.isEnabled = viewModel.modelReady.value
            }
        }
    }

    private fun showResult(result: TriageResult) {
        val triageColor = colorForCode(result.triageCode)
        cardResult.strokeColor = triageColor
        cardResult.visibility = View.VISIBLE

        tvTriageCode.text = result.triageCode.name
        tvTriageCode.setTextColor(triageColor)
        tvConfidence.text = "${(result.confidence * 100).toInt()}% confidence"
        tvReasoning.text = result.reasoning
        tvSteps.text = result.immediateSteps.mapIndexed { i, s -> "${i + 1}. $s" }.joinToString("\n")

        tvTriageCode.scaleX = 0f
        tvTriageCode.scaleY = 0f
        tvTriageCode.animate()
            .scaleX(1f).scaleY(1f)
            .setDuration(400)
            .setInterpolator(OvershootInterpolator(2f))
            .start()

        val surface = ContextCompat.getColor(requireContext(), R.color.surface)
        val tinted = tintedSurface(result.triageCode)
        ValueAnimator.ofArgb(surface, tinted, surface).apply {
            duration = 800
            addUpdateListener { cardResult.setCardBackgroundColor(it.animatedValue as Int) }
            start()
        }
    }

    private fun tintedSurface(code: TriageCode): Int = when (code) {
        TriageCode.RED    -> 0xFF3A1C1C.toInt()
        TriageCode.YELLOW -> 0xFF3A3118.toInt()
        TriageCode.GREEN  -> 0xFF1C3A1E.toInt()
        TriageCode.BLACK  -> 0xFF2A2A2A.toInt()
        TriageCode.UNKNOWN -> 0xFF282828.toInt()
    }

    private fun colorForCode(code: TriageCode): Int = when (code) {
        TriageCode.RED -> requireContext().getColor(R.color.triage_red)
        TriageCode.YELLOW -> requireContext().getColor(R.color.triage_yellow)
        TriageCode.GREEN -> requireContext().getColor(R.color.triage_green)
        TriageCode.BLACK -> requireContext().getColor(R.color.triage_black)
        TriageCode.UNKNOWN -> requireContext().getColor(R.color.triage_unknown)
    }

    private fun startPulse() {
        viewPulse.visibility = View.VISIBLE
        viewPulse.scaleX = 1f; viewPulse.scaleY = 1f; viewPulse.alpha = 0.6f
        val sx = ObjectAnimator.ofFloat(viewPulse, "scaleX", 1f, 2.5f)
        val sy = ObjectAnimator.ofFloat(viewPulse, "scaleY", 1f, 2.5f)
        val al = ObjectAnimator.ofFloat(viewPulse, "alpha", 0.6f, 0f)
        pulseAnimator = AnimatorSet().apply {
            playTogether(sx, sy, al)
            duration = 1000
            addListener(object : android.animation.AnimatorListenerAdapter() {
                override fun onAnimationEnd(a: android.animation.Animator) {
                    if (viewPulse.visibility == View.VISIBLE) {
                        viewPulse.scaleX = 1f; viewPulse.scaleY = 1f; viewPulse.alpha = 0.6f
                        start()
                    }
                }
            })
            start()
        }
    }

    private fun stopPulse() {
        pulseAnimator?.cancel()
        pulseAnimator = null
        viewPulse.visibility = View.INVISIBLE
    }

    private fun slideInNextPatient() {
        btnNextPatient.visibility = View.VISIBLE
        btnNextPatient.translationY = 200f
        btnNextPatient.animate()
            .translationY(0f)
            .setDuration(300)
            .setInterpolator(DecelerateInterpolator())
            .start()
    }

    private fun slideOutNextPatient() {
        if (btnNextPatient.visibility == View.VISIBLE) {
            btnNextPatient.animate()
                .translationY(200f)
                .setDuration(200)
                .withEndAction { btnNextPatient.visibility = View.GONE }
                .start()
        }
    }

    private fun onMicClicked() {
        if (ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.RECORD_AUDIO)
            == PackageManager.PERMISSION_GRANTED) {
            viewModel.startListening()
        } else {
            permissionLauncher.launch(arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.SEND_SMS))
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        pulseAnimator?.cancel()
    }
}
