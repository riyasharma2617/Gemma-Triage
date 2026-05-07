package com.gemma.triage

import org.junit.Assert.assertEquals
import org.junit.Test

class HistoryExpandStateTest {

    @Test
    fun `initial state has no expanded item`() {
        val state = HistoryExpandState()
        assertEquals(-1, state.expandedPosition)
    }

    @Test
    fun `toggle expands an item`() {
        val state = HistoryExpandState()
        state.toggle(2)
        assertEquals(2, state.expandedPosition)
    }

    @Test
    fun `toggle same item collapses it`() {
        val state = HistoryExpandState()
        state.toggle(2)
        state.toggle(2)
        assertEquals(-1, state.expandedPosition)
    }

    @Test
    fun `toggle different item returns old collapsed position`() {
        val state = HistoryExpandState()
        state.toggle(2)
        val collapsed = state.toggle(5)
        assertEquals(5, state.expandedPosition)
        assertEquals(2, collapsed)
    }

    @Test
    fun `toggle when nothing expanded returns -1 as collapsed`() {
        val state = HistoryExpandState()
        val collapsed = state.toggle(3)
        assertEquals(-1, collapsed)
    }
}
