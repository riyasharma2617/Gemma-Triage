package com.gemma.triage

class HistoryExpandState {
    var expandedPosition: Int = -1

    fun toggle(position: Int): Int {
        val old = expandedPosition
        expandedPosition = if (old == position) -1 else position
        return old
    }
}
