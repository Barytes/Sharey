# Pilot latency comparison

Goal: compare baseline and candidate latency measurements under the fixed pilot protocol.

Progress: six fixture observations are available in `files/pilot.csv`, three per variant. The candidate is lower in each paired fixture trial. The approved summarizer computes per-variant means and a candidate-minus-baseline difference.

Constraints: these are artificial software acceptance data, not a randomized experiment or evidence of a population effect. Retain all rows and the original units (milliseconds). Do not claim statistical significance or general performance improvement.

Next step: run the shared complete Skill, inspect its output and propose a larger randomized measurement protocol. One branch can check arithmetic, another can discuss measurement limitations; a combined node should preserve both conclusions.

The project source contains the fixed protocol. The node's Skill reference identifies the complete summarizer and its relative resources.
