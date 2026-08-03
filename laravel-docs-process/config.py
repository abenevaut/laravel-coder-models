"""Pipeline configuration."""

# Ordered list of pipeline module names
PIPELINE_STEPS = [
    "clean_content",
    "detect_version",
    "extract_sections",
    "generate_qa",
]
