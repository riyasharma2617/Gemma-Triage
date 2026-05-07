package com.gemma.triage

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.viewpager2.widget.ViewPager2
import com.google.android.material.tabs.TabLayout
import com.google.android.material.tabs.TabLayoutMediator

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val viewPager = findViewById<ViewPager2>(R.id.viewPager)
        val tabIndicator = findViewById<TabLayout>(R.id.tabIndicator)

        viewPager.adapter = TriagePagerAdapter(this)
        viewPager.isUserInputEnabled = true

        TabLayoutMediator(tabIndicator, viewPager) { tab, position ->
            tab.text = if (position == 0) "Triage" else "History"
        }.attach()
    }
}
