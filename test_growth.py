from macro_engine.pipelines.pillars import run_usa_inflation


inflation = run_usa_inflation()

print("=" * 60)
print("USA INFLATION")
print("=" * 60)

print(f"State Score:       {inflation.state_score:.2f}")
print(f"State Label:       {inflation.state_label}")

print(f"Trend Score:       {inflation.trend_score:.2f}")
print(f"Trend Label:       {inflation.trend_label}")

print(f"Breadth Score:     {inflation.breadth_score:.2f}")
print(f"Breadth Label:     {inflation.breadth_label}")

print(f"Confidence:        {inflation.confidence_score:.2f}")
print(f"Confidence Label:  {inflation.confidence_label}")

print(f"Buckets Used:      {inflation.buckets_used}")

print("\nKey Drivers:")
for driver in inflation.key_drivers:
    print(f"  • {driver}")

print("\nFlags:")
if inflation.flags:
    for flag in inflation.flags:
        print(f"  • {flag}")
else:
    print("  None")