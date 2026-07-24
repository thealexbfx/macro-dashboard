from macro_engine.pipelines.inflation import (
    run_usa_core_inflation_persistence,
)


result = run_usa_core_inflation_persistence()

print("=" * 60)
print("USA CORE INFLATION PERSISTENCE")
print("=" * 60)

print(f"State Score:       {result.state_score:.2f}")
print(f"State Label:       {result.state_label}")
print(f"Trend Score:       {result.trend_score:.2f}")
print(f"Trend Label:       {result.trend_label}")
print(f"Breadth Score:     {result.breadth_score:.2f}")
print(f"Breadth Label:     {result.breadth_label}")
print(f"Confidence:        {result.confidence_score:.2f}")
print(f"Confidence Label:  {result.confidence_label}")
print(f"Indicators Used:   {result.indicators_used}")

print("\nKey Drivers:")
for driver in result.key_drivers:
    print(f"  • {driver}")

print("\nFlags:")
if result.flags:
    for flag in result.flags:
        print(f"  • {flag}")
else:
    print("  None")