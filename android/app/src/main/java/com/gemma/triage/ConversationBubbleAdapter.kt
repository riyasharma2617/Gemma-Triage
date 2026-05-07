package com.gemma.triage

import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.card.MaterialCardView

data class ConversationBubble(val text: String, val isQuestion: Boolean)

class ConversationBubbleAdapter : RecyclerView.Adapter<ConversationBubbleAdapter.ViewHolder>() {

    private var bubbles: List<ConversationBubble> = emptyList()

    fun submitList(list: List<ConversationBubble>) {
        bubbles = list
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_conversation_bubble, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) =
        holder.bind(bubbles[position])

    override fun getItemCount() = bubbles.size

    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val card: MaterialCardView = itemView.findViewById(R.id.cardBubble)
        private val tvText: TextView = itemView.findViewById(R.id.tvBubbleText)

        fun bind(bubble: ConversationBubble) {
            tvText.text = bubble.text
            val ctx = itemView.context
            val params = card.layoutParams as FrameLayout.LayoutParams
            if (bubble.isQuestion) {
                params.gravity = Gravity.START
                card.setCardBackgroundColor(ContextCompat.getColor(ctx, R.color.surface))
            } else {
                params.gravity = Gravity.END
                card.setCardBackgroundColor(ContextCompat.getColor(ctx, R.color.bubble_answer))
            }
            card.layoutParams = params
        }
    }
}
