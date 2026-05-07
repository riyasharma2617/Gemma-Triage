package com.gemma.triage

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
import androidx.transition.AutoTransition
import androidx.transition.TransitionManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.card.MaterialCardView
import com.google.android.material.chip.Chip
import com.gemma.triage.storage.models.TriageRecord
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class HistoryAdapter : RecyclerView.Adapter<HistoryAdapter.ViewHolder>() {

    private var records: List<TriageRecord> = emptyList()
    private val expandState = HistoryExpandState()
    private val dateFormat = SimpleDateFormat("MMM d · HH:mm", Locale.getDefault())

    fun submitList(newRecords: List<TriageRecord>) {
        records = newRecords
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_history_record, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(records[position], position == expandState.expandedPosition) { clickedPos ->
            val old = expandState.toggle(clickedPos)
            if (old != -1 && old != clickedPos) notifyItemChanged(old)
            notifyItemChanged(clickedPos)
        }
    }

    override fun getItemCount() = records.size

    inner class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val card: MaterialCardView = itemView as MaterialCardView
        private val chipCode: Chip = itemView.findViewById(R.id.chipCode)
        private val tvTimestamp: TextView = itemView.findViewById(R.id.tvTimestamp)
        private val tvConfidenceSmall: TextView = itemView.findViewById(R.id.tvConfidenceSmall)
        private val tvTranscriptionPreview: TextView = itemView.findViewById(R.id.tvTranscriptionPreview)
        private val layoutExpanded: LinearLayout = itemView.findViewById(R.id.layoutExpanded)
        private val tvTranscriptionFull: TextView = itemView.findViewById(R.id.tvTranscriptionFull)
        private val tvStepsExpanded: TextView = itemView.findViewById(R.id.tvStepsExpanded)
        private val tvSmsPayload: TextView = itemView.findViewById(R.id.tvSmsPayload)
        private val chipTransmitted: Chip = itemView.findViewById(R.id.chipTransmitted)

        fun bind(record: TriageRecord, isExpanded: Boolean, onToggle: (Int) -> Unit) {
            chipCode.text = record.triageCode
            chipCode.chipBackgroundColor = android.content.res.ColorStateList.valueOf(codeColor(record.triageCode))
            tvTimestamp.text = dateFormat.format(Date(record.timestamp))
            tvConfidenceSmall.text = "${(record.confidence * 100).toInt()}%"
            tvTranscriptionPreview.text = record.transcription

            tvTranscriptionFull.text = record.transcription
            tvStepsExpanded.text = record.immediateSteps
            tvSmsPayload.text = record.smsPayload

            if (record.isTransmitted) {
                chipTransmitted.text = itemView.context.getString(R.string.label_sms_sent)
                chipTransmitted.chipBackgroundColor = android.content.res.ColorStateList.valueOf(0xFF1B5E20.toInt())
            } else {
                chipTransmitted.text = itemView.context.getString(R.string.label_sms_pending)
                chipTransmitted.chipBackgroundColor = android.content.res.ColorStateList.valueOf(0xFF424242.toInt())
            }

            layoutExpanded.visibility = if (isExpanded) View.VISIBLE else View.GONE

            card.setOnClickListener {
                val pos = adapterPosition
                if (pos == RecyclerView.NO_POSITION) return@setOnClickListener
                val rvParent = card.parent as? ViewGroup ?: return@setOnClickListener
                TransitionManager.beginDelayedTransition(rvParent, AutoTransition().apply { duration = 200 })
                onToggle(pos)
            }
        }

        private fun codeColor(code: String): Int = when (code) {
            "RED"    -> 0xFFD32F2F.toInt()
            "YELLOW" -> 0xFFF9A825.toInt()
            "GREEN"  -> 0xFF388E3C.toInt()
            "BLACK"  -> 0xFF424242.toInt()
            else     -> 0xFF757575.toInt()
        }
    }
}
