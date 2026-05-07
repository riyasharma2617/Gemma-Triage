package com.gemma.triage

import androidx.fragment.app.Fragment
import androidx.fragment.app.FragmentActivity
import androidx.viewpager2.adapter.FragmentStateAdapter

class TriagePagerAdapter(activity: FragmentActivity) : FragmentStateAdapter(activity) {
    override fun getItemCount() = 2
    override fun createFragment(position: Int): Fragment = when (position) {
        0 -> TriageFragment()
        else -> HistoryFragment()
    }
}
