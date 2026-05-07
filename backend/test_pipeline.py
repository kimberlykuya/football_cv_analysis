#!/usr/bin/env python
"""Test pipeline with synthetic video."""
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

print("=" * 60)
print("TESTING FLOWTRACE PIPELINE")
print("=" * 60)

# Step 1: Test imports
print("\n1. Testing imports...")
try:
    from backend.graph.flowtrace_graph import run_pipeline
    print("   [OK] Imports successful")
except ImportError as e:
    print(f"   [FAIL] Import error: {e}")
    sys.exit(1)

# Step 2: Run pipeline on synthetic video
print("\n2. Running pipeline on test_video.mp4...")
try:
    test_video = REPO_ROOT / "test_video.mp4"
    result = run_pipeline(
        video_path=str(test_video),
        match_id='test-001',
        team_id='test-team'
    )
    print("   [OK] Pipeline completed")
except Exception as e:
    import traceback
    print(f"   [FAIL] Pipeline failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 3: Validate output structure
print("\n3. Validating output structure...")
required_keys = ['perception_output', 'analysis_output', 'cross_match_report', 'error']
missing = [k for k in required_keys if k not in result]
if missing:
    print(f"   [WARN] Missing output keys: {missing}")
else:
    print("   [OK] All required output keys present")

# Step 4: Check for errors
print("\n4. Checking for pipeline errors...")
if result.get('error'):
    print(f"   [FAIL] Pipeline error: {result['error']}")
    sys.exit(1)
else:
    print("   [OK] No pipeline errors")

# Step 5: Show stats
print("\n5. Pipeline output summary...")
perc = result.get('perception_output', {})
print(f"   - Frames processed: {perc.get('total_frames', 0)}")
print(f"   - FPS: {perc.get('fps', 0)}")

anat = result.get('analysis_output', {})
if anat:
    print(f"   - Tactical events: {len(anat.get('tactical_events', []))}")
    print(f"   - Summary length: {len(anat.get('summary', ''))} chars")
    metrics = anat.get('metrics', {})
    if metrics:
        print(f"   - Metrics: {json.dumps(metrics, indent=6)}")

cross_report = result.get('cross_match_report', '')
print(f"   - Cross-match report: {len(cross_report)} chars")

print("\n" + "=" * 60)
print("[OK] PIPELINE TEST COMPLETE")
print("=" * 60)
