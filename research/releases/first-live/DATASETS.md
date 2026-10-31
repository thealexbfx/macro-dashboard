# First live release: 13 proposed datasets

No production approval or activation has occurred. Exact definitions, rights, attribution and actual non-null coverage are in [selection.json](selection.json).

| Dataset | Canonical ID | Frequency | Stored rows |
|---|---|---|---:|
| Real GDP — Germany | `eurostat_e4b0591cf148660f3349` | quarterly | 195 |
| Real GDP — France | `eurostat_eca8a799de8d6687fe33` | quarterly | 195 |
| Real GDP — Italy | `eurostat_6e1c74c102959c0ded7b` | quarterly | 195 |
| Real GDP — Euro area – 21 countries (from 2026) | `eurostat_fcab9c3216a8c2d01fc9` | quarterly | 195 |
| Industrial production — Euro area – 21 countries (from 2026) | `eurostat_3e9b736c08d1e26f46f5` | monthly | 885 |
| Construction production — Germany | `eurostat_c94d6677ff350bbc29aa` | monthly | 561 |
| CPI ANNUAL RATE 00: ALL ITEMS 2015=100 | `ons_27271ab0b950200f5401` | monthly | 453 |
| Gross Domestic Product: chained volume measures: Seasonally adjusted £m | `ons_a007e11b21ed0f67ccf1` | quarterly | 286 |
| Unemployment rate (aged 16 and over, seasonally adjusted): % | `ons_24df6f5df34ca52bac40` | monthly | 666 |
| All construction work construction output | `ons_f069edbcf1bc4e7ff9c5` | monthly | 200 |
| US commercial crude stocks excluding SPR | `eia_4922b423fe8b2b32866f` | weekly | 2,300 |
| US crude oil field production | `eia_4f9f06aabda8ff167d48` | weekly | 2,283 |
| Lower-48 working natural gas storage | `eia_feda97c6fccc3ab58f53` | weekly | 878 |

Total: 9292 rows, 8502 non-null. All native source missing cells remain null. Euro-area data use the explicitly labelled EA21 source composition, and GB construction is not a whole-UK measure. UK unemployment uses overlapping three-month LFS windows; GDP chained volumes are not nominal pounds/euros. EIA weekly production is a flow estimate; stocks are point-in-time inventories.
