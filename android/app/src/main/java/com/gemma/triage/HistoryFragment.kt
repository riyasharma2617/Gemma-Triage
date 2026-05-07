package com.gemma.triage

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.gemma.triage.viewmodel.TriageViewModel
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class HistoryFragment : Fragment() {

    private val viewModel: TriageViewModel by activityViewModels()
    private val adapter = HistoryAdapter()
    private val dayFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View =
        inflater.inflate(R.layout.fragment_history, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val rvHistory = view.findViewById<RecyclerView>(R.id.rvHistory)
        val tvEmpty = view.findViewById<TextView>(R.id.tvEmpty)
        val tvHeader = view.findViewById<TextView>(R.id.tvHistoryHeader)

        rvHistory.layoutManager = LinearLayoutManager(requireContext())
        rvHistory.adapter = adapter

        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.history.collect { records ->
                adapter.submitList(records)
                if (records.isEmpty()) {
                    tvEmpty.visibility = View.VISIBLE
                    rvHistory.visibility = View.GONE
                    tvHeader.text = getString(R.string.label_patients_today, 0)
                } else {
                    tvEmpty.visibility = View.GONE
                    rvHistory.visibility = View.VISIBLE
                    val today = dayFormat.format(Date())
                    val todayCount = records.count { dayFormat.format(Date(it.timestamp)) == today }
                    tvHeader.text = getString(R.string.label_patients_today, todayCount)
                }
            }
        }
    }
}
