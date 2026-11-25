# Phase 0 finding: connection feasibility experiment

Data period: 2024-07-01 to 2025-06-30 for every source: on-time flights, T-100 passengers and DB1B sold routings (DB1B quarters 2024-3 to 2025-2).

Sold routings come from DB1B, a 10% sample of airline tickets. 2.3% of the sampled one-connection passengers had a leg with no recorded selling airline and were not counted. 0.3% of the sampled one-connection passengers were on routings sold by an airline that is neither a marketing airline in the on-time data nor mapped in configuration (LF 12,009, KG 7,451, SY 7,137, 9K 4,916, 9X 3,281, 3M 2,578, MX 2,541, VC 286, 4B 115, 7H 76, X4 31, KE 3, AM 2, AN 2, ET 2, NZ 2, QF 2, RJ 2, AC 1, BA 1, FJ 1, KL 1, QR 1, VS 1); those routings can never match an itinerary. DB1B fares are not used.

**Decision: GO**

## Go/no-go criteria

| Criterion | Observed | Result |
|---|---|---|
| At least 3 showcase examples | 81 | met |
| Examples across at least 2 hubs | 5 | met |

## Hub selection

Candidates are the airports with the most scheduled departures. Score = equally weighted airline count, scheduled departures and passengers boarded, each scaled to 0-1 across the candidates. Eligible = at least the configured number of qualifying itineraries from origins outside the candidate pool (number in brackets). Weather share = share of scheduled departures with weather-attributed delay or a weather cancellation; the pool median is 1.8%.

| Rank | Airport | Score | Eligible (itineraries) | Departures | Airlines (>= share) | Passengers | Weather share | Weather by season (W / Sp / Su / Au) | Weather peak | Selection |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ATL | 2.167 | yes (22022) | 347,178 | DL, WN | 44,754,615 | 2.4% | 3.1% / 1.9% / 3.5% / 1.0% | summer | selected (score) |
| 2 | DEN | 2.014 | yes (5635) | 314,491 | F9, UA, WN | 37,573,203 | 1.6% | 1.8% / 1.8% / 1.5% / 1.2% | spring | selected (score) |
| 3 | ORD | 1.780 | yes (1408) | 334,448 | AA, UA | 32,483,360 | 2.3% | 3.6% / 2.4% / 2.6% / 0.7% | winter | selected (score) |
| 4 | LAX | 1.756 | yes (391) | 197,826 | AA, AS, DL, NK, UA, WN | 25,708,171 | 0.8% | 1.3% / 0.6% / 0.7% / 0.5% | winter | selected (score) |
| 5 | LAS | 1.744 | no (2) | 192,765 | AA, DL, F9, NK, UA, WN | 25,958,236 | 1.0% | 1.0% / 0.7% / 1.8% / 0.5% | summer |  |
| 6 | MCO | 1.710 | no (2) | 156,572 | AA, B6, DL, F9, NK, UA, WN | 23,537,224 | 3.2% | 1.5% / 2.8% / 5.6% / 3.1% | summer |  |
| 7 | DFW | 1.656 | yes (1324) | 319,707 | AA | 35,982,293 | 4.7% | 6.5% / 7.7% / 3.1% / 1.8% | spring | selected (score) |
| 8 | PHX | 1.383 | yes (36) | 199,986 | AA, DL, UA, WN | 24,007,106 | 0.6% | 0.8% / 0.6% / 0.9% / 0.3% | summer | selected (score) |
| 9 | SFO | 1.196 | yes (315) | 145,712 | AA, AS, DL, UA, WN | 18,431,583 | 0.8% | 1.4% / 0.5% / 0.6% / 0.7% | winter | selected (score) |
| 10 | SEA | 1.117 | yes (1636) | 185,450 | AS, DL, UA | 22,332,495 | 1.2% | 2.6% / 0.6% / 0.9% / 0.7% | winter |  |
| 11 | CLT | 1.105 | yes (496) | 252,782 | AA | 24,997,396 | 4.5% | 3.9% / 2.6% / 9.0% / 2.3% | summer |  |
| 12 | TPA | 1.079 | no (0) | 78,529 | AA, B6, DL, F9, NK, UA, WN | 11,139,765 | 3.3% | 1.4% / 1.7% / 4.9% / 5.5% | autumn |  |
| 13 | LGA | 1.021 | yes (212) | 164,171 | AA, DL, UA, WN | 15,687,494 | 1.7% | 2.4% / 1.0% / 2.9% / 0.5% | summer |  |
| 14 | DCA | 1.019 | yes (42) | 145,401 | AA, B6, DL, UA, WN | 12,105,640 | 3.3% | 5.5% / 2.3% / 4.5% / 0.8% | winter |  |
| 15 | FLL | 1.000 | no (3) | 87,938 | AA, B6, DL, NK, UA, WN | 13,045,416 | 2.2% | 1.2% / 1.8% / 4.0% / 1.8% | summer |  |
| 16 | BOS | 0.990 | no (3) | 146,971 | AA, B6, DL, UA | 16,877,119 | 1.4% | 3.4% / 0.6% / 1.4% / 0.5% | winter |  |
| 17 | EWR | 0.929 | yes (77) | 135,548 | AA, DL, NK, UA | 16,182,995 | 2.1% | 2.1% / 1.9% / 4.4% / 0.3% | summer |  |
| 18 | IAH | 0.921 | yes (705) | 169,612 | AA, NK, UA | 17,366,973 | 3.2% | 3.9% / 3.1% / 5.3% / 0.7% | summer |  |
| 19 | MSP | 0.902 | yes (1416) | 129,155 | AA, DL, UA, WN | 16,056,936 | 1.7% | 2.2% / 1.8% / 2.1% / 0.7% | winter |  |
| 20 | SAN | 0.846 | yes (15) | 97,507 | AA, AS, DL, UA, WN | 12,229,614 | 1.7% | 3.4% / 1.3% / 1.1% / 1.1% | winter |  |
| 21 | SLC | 0.759 | yes (2290) | 114,860 | AA, DL, UA, WN | 12,790,508 | 1.0% | 1.8% / 0.6% / 1.1% / 0.6% | winter |  |
| 22 | DTW | 0.720 | yes (775) | 137,392 | AA, DL, NK | 14,399,427 | 1.7% | 2.6% / 1.4% / 1.8% / 0.9% | winter |  |
| 23 | BNA | 0.693 | no (0) | 103,686 | AA, DL, UA, WN | 11,903,493 | 1.9% | 2.6% / 2.4% / 2.0% / 0.7% | winter |  |
| 24 | JFK | 0.660 | yes (184) | 124,207 | AA, B6, DL | 13,979,649 | 1.2% | 2.2% / 0.6% / 1.8% / 0.4% | winter |  |
| 25 | PHL | 0.642 | no (2) | 125,602 | AA, DL, F9 | 13,165,326 | 2.6% | 3.1% / 2.0% / 4.6% / 0.6% | summer |  |
| 26 | MIA | 0.632 | yes (69) | 110,704 | AA, DL, UA | 14,762,732 | 2.8% | 1.2% / 2.2% / 5.8% / 2.1% | summer |  |
| 27 | AUS | 0.575 | no (11) | 85,643 | AA, DL, UA, WN | 10,038,184 | 2.0% | 1.8% / 2.8% / 2.5% / 0.7% | spring |  |
| 28 | BWI | 0.510 | no (0) | 97,383 | DL, NK, WN | 12,127,215 | 1.7% | 2.3% / 1.2% / 2.4% / 0.7% | summer |  |
| 29 | IAD | 0.221 | yes (443) | 90,580 | DL, UA | 8,613,218 | 2.5% | 3.5% / 1.7% / 4.2% / 0.4% | summer |  |
| 30 | MDW | 0.023 | no (0) | 75,953 | WN | 9,452,045 | 1.2% | 1.6% / 1.1% / 1.4% / 0.7% | winter |  |

**Unmet constraints:** none

## Airlines covered

Itineraries through the selected hubs by marketing airline (inbound flight), next to the sampled DB1B passengers on sold routings through the same hubs with one airline on both legs.

| Airline | Itineraries | Sold passengers, same-airline routings |
|---|---|---|
| AA | 2,197 | 2,351,532 |
| DL | 35,058 | 2,048,616 |
| UA | 10,291 | 1,726,378 |
| WN | 0 | 750,552 |
| F9 | 15 | 241,053 |
| NK | 0 | 37,632 |
| AS | 10 | 34,958 |
| HA | 0 | 1,028 |
| B6 | 0 | 187 |
| NZ | 0 | 2 |
| AC | 0 | 1 |
| AM | 0 | 1 |
| MX | 0 | 1 |

**No itineraries:** WN, NK, HA, B6, NZ, AC, AM, MX. An itinerary is identified by flight number, and each flight must be scheduled on at least 60% of days, so an airline that reassigns flight numbers often (Southwest does) can sell many connections without any qualifying itinerary.

## Origin/destination pairs

Pairs are chosen from the data: candidates have at least two qualifying itineraries through the selected hubs and are ranked by their number of comparable itinerary pairs (same origin and destination, scheduled travel time and departure time close together).

| Rank | Pair | Regional origin | Main hub | Comparable pairs | Itineraries |
|---|---|---|---|---|---|
| 1 | MCO-LGA | yes | ATL | 147 | 37 |
| 2 | LGA-MCO | yes | ATL | 142 | 36 |
| 3 | MCO-LAX | yes | ATL | 80 | 27 |
| 81 | SAN-IAD | yes | DEN | 22 | 12 |
| 84 | IND-SFO | yes | ORD | 21 | 13 |
| 116 | ATL-SMF | no | LAX | 18 | 11 |
| 178 | CLE-SFO | yes | ORD | 15 | 11 |
| 190 | BOS-SFO | yes | DEN | 14 | 12 |
| 199 | EWR-MKE | yes | ORD | 14 | 13 |
| 219 | BNA-DEN | yes | DFW | 13 | 12 |
| 238 | LAX-IAD | no | DEN | 13 | 10 |
| 294 | ATL-SEA | no | LAX | 11 | 11 |
| 295 | ATL-SFO | no | LAX | 11 | 10 |
| 335 | SLC-ATL | yes | DFW | 11 | 10 |
| 409 | DEN-HNL | no | SFO | 9 | 10 |

10 of 15 selected pairs have a regional origin.

**Not selected:** 9972 other candidate pairs.

**Selection shortfalls:** none

**Pairs without qualifying itineraries:** none

## Itinerary rules applied

For each selected pair, candidates are flight pairs through a selected hub, sold by the same airline or a partner pair, with each flight scheduled on most days. The rules then remove, in order: a median scheduled layover outside the limits; a routing not sold, meaning DB1B does not show at least 30 sampled passengers on that routing and pair of selling airlines over the period; and flights that connect on fewer than 60% of days in the period.

| Pair | Candidates | Layover outside limits | Routing not sold | Connect on too few days | Qualifying |
|---|---|---|---|---|---|
| ATL-SEA | 170 | 148 | 9 | 2 | 11 |
| ATL-SFO | 122 | 106 | 0 | 6 | 10 |
| ATL-SMF | 82 | 66 | 1 | 4 | 11 |
| BNA-DEN | 116 | 91 | 1 | 12 | 12 |
| BOS-SFO | 122 | 103 | 0 | 7 | 12 |
| CLE-SFO | 77 | 59 | 0 | 7 | 11 |
| DEN-HNL | 91 | 75 | 2 | 4 | 10 |
| EWR-MKE | 103 | 84 | 1 | 5 | 13 |
| IND-SFO | 91 | 66 | 0 | 12 | 13 |
| LAX-IAD | 115 | 95 | 0 | 10 | 10 |
| LGA-MCO | 238 | 192 | 1 | 9 | 36 |
| MCO-LAX | 205 | 169 | 0 | 9 | 27 |
| MCO-LGA | 250 | 203 | 3 | 7 | 37 |
| SAN-IAD | 70 | 55 | 0 | 3 | 12 |
| SLC-ATL | 204 | 180 | 12 | 2 | 10 |

## Showcase examples

Pairs of comparable itineraries, both with sufficient data and not assumption-sensitive, whose connection feasibility differs by at least the showcase threshold with a 95% confidence interval that excludes zero.

81 showcase examples in 9 origin/destination pairs, across 5 hubs. The strongest example per pair is shown; every example is listed in summary.json.

58 of 81 examples were compared at all 9 settings of minimum connection time and boarding cutoff (fewest: 6); at the remaining settings an itinerary did not qualify or had insufficient data, so the order could not be checked there. Connection feasibility depends only on these two settings; the recurrence threshold changes which itineraries qualify. Of the others: 23 not at minimum connection 45 min.

In 11 of 81 examples the lower itinerary's scheduled layover is shorter than its feasibility threshold (minimum connection time plus boarding cutoff): its connection is feasible only on days when the inbound flight arrives early or the outbound leaves late.

| Pair | Itinerary A | Connection feasibility A | Itinerary B | Connection feasibility B | Difference | Scheduled layover A / B (min) | Sold passengers on routing A / B (DB1B sample; shared by its itineraries) | Settings compared | Shared dates | Comparability |
|---|---|---|---|---|---|---|---|---|---|---|
| EWR-MKE | EWR-ORD-MKE:UA661+UA5262 (ORD) | 94% (218 of 233 days) | EWR-ATL-MKE:DL2340+DL1268 (ATL) | 53% (120 of 225 days) | +40 points (95% CI +33 to +47) | 153 / 68 | 221 on 7 itineraries / 93 on 6 itineraries | 9 of 9 | 137 | travel time within 31 min, departure within 126 min |
| MCO-LGA | MCO-ATL-LGA:DL1548+DL513 (ATL) | 95% (315 of 331 days) | MCO-ATL-LGA:DL1494+DL513 (ATL) | 61% (209 of 344 days) | +34 points (95% CI +29 to +40) | 90 / 44 (tighter than threshold) | 44 on 36 itineraries / 44 on 36 itineraries | 6 of 9 (not at minimum connection 45 min) | 323 | travel time within 45 min, departure within 45 min |
| MCO-LAX | MCO-ATL-LAX:DL1213+DL753 (ATL) | 92% (311 of 337 days) | MCO-ATL-LAX:DL1658+DL753 (ATL) | 60% (133 of 220 days) | +32 points (95% CI +25 to +39) | 91 / 39 (tighter than threshold) | 186 on 25 itineraries / 186 on 25 itineraries | 6 of 9 (not at minimum connection 45 min) | 220 | travel time within 55 min, departure within 60 min |
| LGA-MCO | LGA-ATL-MCO:DL994+DL1497 (ATL) | 93% (291 of 314 days) | LGA-ATL-MCO:DL974+DL2035 (ATL) | 67% (205 of 305 days) | +25 points (95% CI +20 to +31) | 100 / 42 (tighter than threshold) | 64 on 33 itineraries / 64 on 33 itineraries | 6 of 9 (not at minimum connection 45 min) | 283 | travel time within 51 min, departure within 121 min |
| ATL-SFO | ATL-LAX-SFO:DL500+DL2986 (LAX) | 85% (195 of 229 days) | ATL-DFW-SFO:AA2403+AA446 (DFW) | 64% (145 of 228 days) | +22 points (95% CI +14 to +29) | 98 / 50 | 65 on 6 itineraries / 433 on 1 itineraries | 9 of 9 | 178 | travel time within 42 min, departure within 112 min |
| ATL-SEA | ATL-ORD-SEA:UA516+UA2211 (ORD) | 97% (266 of 273 days) | ATL-LAX-SEA:DL301+DL1551 (LAX) | 76% (176 of 231 days) | +21 points (95% CI +16 to +27) | 175 / 92 | 65 on 1 itineraries / 39 on 7 itineraries | 9 of 9 | 160 | travel time within 36 min, departure within 75 min |
| BNA-DEN | BNA-ATL-DEN:DL3159+DL746 (ATL) | 95% (314 of 329 days) | BNA-DFW-DEN:AA1100+AA2235 (DFW) | 75% (165 of 220 days) | +20 points (95% CI +14 to +27) | 108 / 61 | 187 on 5 itineraries / 203 on 6 itineraries | 9 of 9 | 187 | travel time within 48 min, departure within 57 min |
| SAN-IAD | SAN-DEN-IAD:UA2476+UA347 (DEN) | 93% (245 of 263 days) | SAN-LAX-IAD:UA4723+UA1140 (LAX) | 78% (175 of 225 days) | +15 points (95% CI +9 to +22) | 82 / 60 | 83 on 5 itineraries / 49 on 3 itineraries | 6 of 9 (not at minimum connection 45 min) | 166 | travel time within 6 min, departure within 150 min |
| LAX-IAD | LAX-ATL-IAD:DL395+DL2549 (ATL) | 89% (292 of 327 days) | LAX-ATL-IAD:DL715+DL2549 (ATL) | 76% (173 of 227 days) | +13 points (95% CI +7 to +19) | 102 / 62 | 134 on 4 itineraries / 134 on 4 itineraries | 6 of 9 (not at minimum connection 45 min) | 191 | travel time within 40 min, departure within 71 min |

## Breakdown of the showcase examples

| Pair | Showcase examples |
|---|---|
| MCO-LGA | 37 |
| MCO-LAX | 15 |
| LGA-MCO | 12 |
| EWR-MKE | 5 |
| ATL-SEA | 4 |
| SAN-IAD | 4 |
| BNA-DEN | 2 |
| ATL-SFO | 1 |
| LAX-IAD | 1 |

19 of 81 examples compare itineraries through different hubs; the rest compare flights through the same hub.

Without the examples whose lower itinerary is scheduled tighter than its feasibility threshold, 70 examples, in 9 pairs and across 5 hubs (ATL, DEN, DFW, LAX, ORD), remain.

In 66 of 81 examples the slower itinerary takes more than 1.5 times the median scheduled nonstop time on the same pair (at most 2.9 times). These routings are sold, so they stay in. 0 examples have no nonstop to compare with.

## Sensitivity to assumptions

Every analyzed itinerary is re-evaluated under each combination of minimum connection time, boarding cutoff and recurrence threshold, with the hub and origin/destination pair selection fixed. A comparable pair is assumption-sensitive when its order by connection feasibility reverses in any scenario.

| Scenario | Min. connection (min) | Boarding cutoff (min) | Recurrence | Itineraries | Sufficient data | Median connection feasibility | Comparable pairs reversed |
|---|---|---|---|---|---|---|---|
| mct20_cut10_rec50 | 20 | 10 | 50% | 304 | 304 | 94% | 52 |
| mct20_cut10_rec60 | 20 | 10 | 60% | 244 | 244 | 95% | 52 |
| mct20_cut10_rec75 | 20 | 10 | 75% | 147 | 147 | 95% | 25 |
| mct20_cut15_rec50 | 20 | 15 | 50% | 304 | 304 | 94% | 40 |
| mct20_cut15_rec60 | 20 | 15 | 60% | 244 | 244 | 94% | 40 |
| mct20_cut15_rec75 | 20 | 15 | 75% | 147 | 147 | 95% | 16 |
| mct20_cut20_rec50 | 20 | 20 | 50% | 304 | 304 | 93% | 22 |
| mct20_cut20_rec60 | 20 | 20 | 60% | 244 | 244 | 94% | 22 |
| mct20_cut20_rec75 | 20 | 20 | 75% | 147 | 147 | 95% | 7 |
| mct30_cut10_rec50 | 30 | 10 | 50% | 290 | 290 | 94% | 9 |
| mct30_cut10_rec60 | 30 | 10 | 60% | 235 | 235 | 94% | 9 |
| mct30_cut10_rec75 | 30 | 10 | 75% | 138 | 138 | 95% | 3 |
| mct30_cut15_rec50 | 30 | 15 | 50% | 290 | 290 | 93% | 0 |
| mct30_cut15_rec60 (default) | 30 | 15 | 60% | 235 | 235 | 94% | 0 |
| mct30_cut15_rec75 | 30 | 15 | 75% | 138 | 138 | 95% | 0 |
| mct30_cut20_rec50 | 30 | 20 | 50% | 290 | 290 | 93% | 16 |
| mct30_cut20_rec60 | 30 | 20 | 60% | 235 | 235 | 93% | 16 |
| mct30_cut20_rec75 | 30 | 20 | 75% | 138 | 138 | 95% | 9 |
| mct45_cut10_rec50 | 45 | 10 | 50% | 270 | 270 | 93% | 44 |
| mct45_cut10_rec60 | 45 | 10 | 60% | 217 | 217 | 94% | 36 |
| mct45_cut10_rec75 | 45 | 10 | 75% | 124 | 124 | 95% | 16 |
| mct45_cut15_rec50 | 45 | 15 | 50% | 270 | 270 | 93% | 55 |
| mct45_cut15_rec60 | 45 | 15 | 60% | 217 | 217 | 94% | 48 |
| mct45_cut15_rec75 | 45 | 15 | 75% | 124 | 124 | 95% | 22 |
| mct45_cut20_rec50 | 45 | 20 | 50% | 270 | 270 | 92% | 67 |
| mct45_cut20_rec60 | 45 | 20 | 60% | 217 | 217 | 93% | 60 |
| mct45_cut20_rec75 | 45 | 20 | 75% | 124 | 124 | 94% | 26 |

**Assumption-sensitive pairs:** ATL-DEN-SFO:UA235+UA2681 vs ATL-LAX-SFO:DL500+DL2986, ATL-DEN-SFO:UA340+UA1561 vs ATL-LAX-SFO:DL501+DL2267, ATL-LAX-SEA:DL501+DL2606 vs ATL-LAX-SEA:DL898+DL1045, ATL-LAX-SFO:DL501+DL2267 vs ATL-DEN-SFO:UA1327+UA1812, ATL-LAX-SFO:DL895+DL1559 vs ATL-LAX-SFO:DL501+DL2267, ATL-LAX-SFO:DL898+DL2267 vs ATL-DEN-SFO:UA340+UA1561, ATL-LAX-SFO:DL898+DL2267 vs ATL-LAX-SFO:DL501+DL2267, ATL-LAX-SFO:DL996+DL2272 vs ATL-LAX-SFO:DL501+DL2267, ATL-LAX-SMF:DL753+DL3712 vs ATL-DEN-SMF:UA235+UA2132, ATL-LAX-SMF:DL895+DL3712 vs ATL-DEN-SMF:UA1327+UA1208, ATL-LAX-SMF:DL895+DL3712 vs ATL-LAX-SMF:DL501+DL3759, ATL-LAX-SMF:DL895+DL3712 vs ATL-LAX-SMF:DL673+DL3759, ATL-LAX-SMF:DL898+DL3812 vs ATL-DEN-SMF:UA340+UA1415, BNA-ATL-DEN:DL3001+DL706 vs BNA-DFW-DEN:AA2787+AA2359, BNA-ATL-DEN:DL3069+DL530 vs BNA-ATL-DEN:DL3001+DL706, BNA-DFW-DEN:AA2244+AA577 vs BNA-DFW-DEN:AA1100+AA2235, BNA-DFW-DEN:AA2244+AA577 vs BNA-DFW-DEN:AA2238+AA662, BOS-ATL-SFO:DL973+DL823 vs BOS-ATL-SFO:DL376+DL517, BOS-DEN-SFO:UA647+UA1561 vs BOS-DEN-SFO:UA662+UA1812, BOS-ORD-SFO:UA1414+UA343 vs BOS-ATL-SFO:DL695+DL531, CLE-DEN-SFO:UA1690+UA1561 vs CLE-ORD-SFO:UA609+UA1878, DEN-LAX-HNL:DL2828+DL443 vs DEN-SFO-HNL:UA1561+UA1509, DEN-SFO-HNL:UA2041+UA300 vs DEN-LAX-HNL:UA405+UA1431, DEN-SFO-HNL:UA573+UA1175 vs DEN-LAX-HNL:UA1093+UA1158, DEN-SFO-HNL:UA573+UA1175 vs DEN-PHX-HNL:AA1404+AA692, EWR-ATL-MKE:DL2365+DL1246 vs EWR-ATL-MKE:DL1673+DL1246, EWR-ATL-MKE:DL2365+DL1246 vs EWR-ATL-MKE:DL2325+DL2152, EWR-ORD-MKE:UA1144+UA5320 vs EWR-ORD-MKE:UA661+UA5262, EWR-ORD-MKE:UA661+UA5320 vs EWR-ATL-MKE:DL2340+DL1268, IND-ORD-SFO:UA3565+UA343 vs IND-ORD-SFO:UA3483+UA1387, IND-ORD-SFO:UA3677+UA1577 vs IND-ORD-SFO:UA3565+UA1878, LAX-ATL-IAD:DL390+DL1695 vs LAX-ATL-IAD:DL515+DL2902, LAX-DFW-IAD:AA2811+AA1863 vs LAX-DEN-IAD:UA1912+UA347, LGA-ATL-MCO:DL342+DL1030 vs LGA-ATL-MCO:DL364+DL1576, LGA-ATL-MCO:DL342+DL1030 vs LGA-ATL-MCO:DL550+DL664, LGA-ATL-MCO:DL364+DL1030 vs LGA-ATL-MCO:DL342+DL664, LGA-ATL-MCO:DL364+DL1030 vs LGA-ATL-MCO:DL550+DL1658, LGA-ATL-MCO:DL364+DL1372 vs LGA-ATL-MCO:DL992+DL1150, LGA-ATL-MCO:DL364+DL1576 vs LGA-ATL-MCO:DL993+DL1742, LGA-ATL-MCO:DL364+DL1576 vs LGA-ORD-MCO:UA2389+UA2323, LGA-ATL-MCO:DL968+DL1733 vs LGA-ATL-MCO:DL969+DL1733, LGA-ATL-MCO:DL974+DL1733 vs LGA-ATL-MCO:DL990+DL1497, LGA-ATL-MCO:DL974+DL2881 vs LGA-ATL-MCO:DL968+DL1162, LGA-ATL-MCO:DL974+DL2881 vs LGA-ATL-MCO:DL994+DL1497, LGA-ATL-MCO:DL988+DL2035 vs LGA-ATL-MCO:DL969+DL1733, LGA-ATL-MCO:DL988+DL2035 vs LGA-ATL-MCO:DL990+DL1742, LGA-ATL-MCO:DL988+DL2035 vs LGA-ATL-MCO:DL993+DL1150, LGA-ATL-MCO:DL988+DL2881 vs LGA-ATL-MCO:DL993+DL1497, LGA-ATL-MCO:DL989+DL1150 vs LGA-ATL-MCO:DL992+DL1372, LGA-ATL-MCO:DL989+DL1372 vs LGA-ATL-MCO:DL364+DL1030, LGA-ATL-MCO:DL989+DL1372 vs LGA-ATL-MCO:DL992+DL1576, LGA-ATL-MCO:DL990+DL1742 vs LGA-ATL-MCO:DL989+DL1372, LGA-ATL-MCO:DL990+DL2035 vs LGA-ATL-MCO:DL992+DL1150, LGA-ATL-MCO:DL992+DL1372 vs LGA-ORD-MCO:UA2389+UA2323, LGA-ATL-MCO:DL993+DL1150 vs LGA-ATL-MCO:DL989+DL1372, LGA-ATL-MCO:DL993+DL1150 vs LGA-ATL-MCO:DL990+DL1742, LGA-ATL-MCO:DL993+DL1497 vs LGA-ORD-MCO:UA1310+UA2042, LGA-ATL-MCO:DL993+DL1742 vs LGA-ATL-MCO:DL988+DL2881, LGA-ATL-MCO:DL993+DL1742 vs LGA-ATL-MCO:DL989+DL1150, LGA-ATL-MCO:DL994+DL1497 vs LGA-ATL-MCO:DL988+DL2035, LGA-ATL-MCO:DL994+DL2035 vs LGA-ATL-MCO:DL993+DL1742, MCO-ATL-LAX:DL1030+DL301 vs MCO-ATL-LAX:DL1576+DL500, MCO-ATL-LAX:DL1030+DL301 vs MCO-DEN-LAX:UA1520+UA564, MCO-ATL-LAX:DL1150+DL331 vs MCO-ATL-LAX:DL1576+DL500, MCO-ATL-LAX:DL1213+DL753 vs MCO-ATL-LAX:DL2204+DL895, MCO-ATL-LAX:DL1213+DL753 vs MCO-ATL-LAX:DL664+DL301, MCO-ATL-LAX:DL1372+DL319 vs MCO-ATL-LAX:DL1576+DL500, MCO-ATL-LAX:DL1446+DL501 vs MCO-ATL-LAX:DL1463+DL673, MCO-ATL-LAX:DL1446+DL501 vs MCO-ATL-LAX:DL1548+DL898, MCO-ATL-LAX:DL1446+DL673 vs MCO-ATL-LAX:DL1463+DL673, MCO-ATL-LAX:DL1446+DL673 vs MCO-ATL-LAX:DL1548+DL501, MCO-ATL-LAX:DL1463+DL501 vs MCO-ATL-LAX:DL1505+DL673, MCO-ATL-LAX:DL1463+DL895 vs MCO-ATL-LAX:DL1494+DL501, MCO-ATL-LAX:DL1494+DL501 vs MCO-ATL-LAX:DL1463+DL673, MCO-ATL-LAX:DL1494+DL898 vs MCO-ATL-LAX:DL1505+DL673, MCO-ATL-LAX:DL664+DL301 vs MCO-ATL-LAX:DL1030+DL301, MCO-ATL-LAX:DL664+DL301 vs MCO-ATL-LAX:DL1576+DL500, MCO-ATL-LAX:DL664+DL301 vs MCO-DEN-LAX:UA1520+UA564, MCO-ATL-LGA:DL1030+DL468 vs MCO-ATL-LGA:DL664+DL434, MCO-ATL-LGA:DL1446+DL371 vs MCO-ATL-LGA:DL1494+DL557, MCO-ATL-LGA:DL1446+DL467 vs MCO-ATL-LGA:DL1463+DL467, MCO-ATL-LGA:DL1446+DL467 vs MCO-ATL-LGA:DL1494+DL371, MCO-ATL-LGA:DL1463+DL371 vs MCO-ATL-LGA:DL1213+DL460, MCO-ATL-LGA:DL1463+DL371 vs MCO-ATL-LGA:DL1446+DL557, MCO-ATL-LGA:DL1463+DL371 vs MCO-ATL-LGA:DL1494+DL513, MCO-ATL-LGA:DL1463+DL460 vs MCO-ATL-LGA:DL1494+DL467, MCO-ATL-LGA:DL1463+DL467 vs MCO-ATL-LGA:DL1213+DL433, MCO-ATL-LGA:DL1463+DL467 vs MCO-ATL-LGA:DL1446+DL371, MCO-ATL-LGA:DL1463+DL467 vs MCO-ATL-LGA:DL1494+DL557, MCO-ATL-LGA:DL1463+DL467 vs MCO-ATL-LGA:DL1548+DL513, MCO-ATL-LGA:DL1463+DL525 vs MCO-ATL-LGA:DL1494+DL467, MCO-ATL-LGA:DL1494+DL371 vs MCO-ATL-LGA:DL1463+DL467, MCO-ATL-LGA:DL1494+DL371 vs MCO-ATL-LGA:DL1494+DL557, MCO-ATL-LGA:DL1505+DL467 vs MCO-ATL-LGA:DL1213+DL460, MCO-ATL-LGA:DL1505+DL467 vs MCO-ATL-LGA:DL1463+DL371, MCO-ATL-LGA:DL1505+DL525 vs MCO-ATL-LGA:DL2204+DL460, MCO-ATL-LGA:DL1548+DL557 vs MCO-ATL-LGA:DL1446+DL467, MCO-ATL-LGA:DL1548+DL557 vs MCO-ATL-LGA:DL1463+DL467, MCO-ATL-LGA:DL1548+DL557 vs MCO-ATL-LGA:DL1494+DL371, MCO-ATL-LGA:DL1576+DL490 vs MCO-ATL-LGA:DL1576+DL468, MCO-ATL-LGA:DL2204+DL433 vs MCO-ATL-LGA:DL1505+DL460, MCO-ATL-LGA:DL2204+DL433 vs MCO-ATL-LGA:DL664+DL434, MCO-ATL-LGA:DL2204+DL525 vs MCO-ATL-LGA:DL1213+DL460, MCO-ATL-LGA:DL2204+DL525 vs MCO-ATL-LGA:DL1505+DL467, MCO-DEN-LAX:UA1520+UA2240 vs MCO-ATL-LAX:DL1658+DL301, MCO-DEN-LAX:UA1520+UA564 vs MCO-ATL-LAX:DL1576+DL500, SAN-ATL-IAD:DL725+DL1309 vs SAN-DEN-IAD:UA264+UA798, SAN-ATL-IAD:DL729+DL1695 vs SAN-ATL-IAD:DL762+DL2902, SAN-ATL-IAD:DL729+DL1695 vs SAN-DFW-IAD:AA2535+AA1863, SAN-ATL-IAD:DL729+DL1695 vs SAN-LAX-IAD:UA4723+UA1140, SAN-ATL-IAD:DL762+DL2902 vs SAN-DFW-IAD:AA2535+AA1863, SAN-ATL-IAD:DL762+DL2902 vs SAN-LAX-IAD:UA5249+UA1635, SAN-DEN-IAD:UA2476+UA347 vs SAN-ATL-IAD:DL729+DL1695, SAN-DEN-IAD:UA2476+UA347 vs SAN-ATL-IAD:DL762+DL2902, SAN-LAX-IAD:UA5249+UA1635 vs SAN-ATL-IAD:DL725+DL1309, SAN-LAX-IAD:UA5249+UA1635 vs SAN-DEN-IAD:UA264+UA798, SLC-DEN-ATL:UA1790+UA1305 vs SLC-DFW-ATL:AA2066+AA2403, SLC-DFW-ATL:DL2798+DL414 vs SLC-PHX-ATL:DL1447+DL348, SLC-DFW-ATL:DL2800+DL32 vs SLC-DFW-ATL:AA2195+AA1248, SLC-PHX-ATL:DL1447+DL348 vs SLC-DFW-ATL:DL2800+DL32

2595 pair-scenario combinations could not be compared because an itinerary did not qualify or had insufficient data in that scenario; they are not counted as reversals.

## Confidence interval method

Paired day-level bootstrap: the service dates on which either itinerary has a paired outcome are resampled with replacement (10,000 times, seed 20261124); each itinerary's feasibility rate is computed on the drawn dates where it has an outcome, and the interval is the central 95% of the differences. A showcase also needs both itineraries observed on at least the minimum sample size of the same dates. Resampling whole dates keeps the correlation between itineraries flying on the same day (shared weather and congestion), as FR-029 requires.

## Known limitations

- Airlines sometimes hold an outbound flight for connecting passengers. The data cannot show this, so some days classified as insufficient time may have worked in practice.
- Gate changes and the walking distance between gates are not in the data.
- How full flights were is not considered: a feasible connection does not mean a seat was available.
- Transfer time is assumed (the hub's minimum connection time), not measured.
- Results are historical frequencies for the data period, not a prediction of future connection feasibility.
- Weather is measured only through BTS weather-attributed delays and weather cancellations; weather recorded under National Aviation System delays is not counted.
- Many comparisons are made, each at the stated confidence level, with no multiple-comparison correction, so a single example can be a chance result; the decision rests on the number and spread of examples.
- Sold routings come from DB1B, a 10% ticket sample: a routing sold rarely may have fewer sampled passengers than the minimum and be left out. DB1B records the selling airline, not the flight numbers, so a sold routing qualifies every flight pair on it that meets the other rules.
- Itineraries are identified by flight number. Airlines that reassign flight numbers often, such as Southwest, have few flights scheduled on most days under one number, so their connections are largely missing; the report lists itineraries per airline.

## Data quality

Excluded from every sample: clock_time_mismatch: 114, conflicting_duplicate: 0, duplicate: 0, invalid_schedule: 2, missing_actual_times: 0. Kept and counted as failures: cancelled: 109,982, diverted: 19,155. Counts by month are in quality.json.

## Connection feasibility

Data period: 2024-07-01 to 2025-06-30. Connection feasibility is the share of paired days on which the scheduled connection would have been possible: the outbound flight's actual gate departure was at least the boarding cutoff plus the minimum connection time after the inbound flight's actual gate arrival. It is a historical frequency, not a prediction, and it does not describe what happened to any traveler. Cancellations and diversions are counted as failures and shown separately. Itineraries with fewer than 30 paired days show "insufficient data" instead of a rate.

| Itinerary | Hub | Connection feasibility | Insufficient time | Cancelled | Diverted | Slack min / p10 / p50 / p90 (minutes) | Excluded days: not connecting / data quality |
|---|---|---|---|---|---|---|---|
| ATL-DEN-SEA:UA235+UA2651 | DEN | 94% (248 of 263 days) | 7 | 5 | 3 | -247 / 134 / 186 / 228 | 99 / 0 |
| ATL-DEN-SEA:UA235+UA299 | DEN | 88% (275 of 313 days) | 33 | 2 | 3 | -284 / 43 / 75 / 119 | 49 / 0 |
| ATL-DEN-SEA:UA340+UA690 | DEN | 94% (221 of 236 days) | 8 | 6 | 1 | -118 / 76 / 176 / 230 | 72 / 0 |
| ATL-DEN-SFO:UA1327+UA1812 | DEN | 87% (225 of 260 days) | 33 | 2 | 0 | -249 / 41 / 74 / 96 | 36 / 0 |
| ATL-DEN-SFO:UA235+UA2681 | DEN | 87% (266 of 306 days) | 32 | 4 | 4 | -339 / 42 / 85 / 150 | 56 / 0 |
| ATL-DEN-SFO:UA340+UA1561 | DEN | 96% (296 of 308 days) | 6 | 6 | 0 | -726 / 84 / 167 / 201 | 0 / 0 |
| ATL-DEN-SMF:UA1327+UA1208 | DEN | 97% (287 of 296 days) | 2 | 7 | 0 | -479 / 149 / 211 / 246 | 0 / 0 |
| ATL-DEN-SMF:UA235+UA2132 | DEN | 89% (322 of 362 days) | 32 | 5 | 3 | -288 / 49 / 96 / 139 | 0 / 0 |
| ATL-DEN-SMF:UA340+UA1415 | DEN | 95% (293 of 308 days) | 8 | 7 | 0 | -718 / 83 / 161 / 197 | 0 / 0 |
| ATL-DFW-SFO:AA2403+AA446 | DFW | 64% (145 of 228 days) | 69 | 14 | 0 | -1090 / -21 / 60 / 138 | 24 / 0 |
| ATL-DFW-SMF:AA1567+AA2448 | DFW | 93% (221 of 237 days) | 5 | 11 | 0 | -364 / 136 / 164 / 202 | 128 / 0 |
| ATL-LAX-SEA:DL301+DL1551 | LAX | 76% (176 of 231 days) | 51 | 4 | 0 | -408 / 21 / 83 / 220 | 134 / 0 |
| ATL-LAX-SEA:DL501+DL2606 | LAX | 90% (326 of 364 days) | 33 | 5 | 0 | -221 / 46 / 82 / 144 | 1 / 0 |
| ATL-LAX-SEA:DL753+DL2640 | LAX | 91% (264 of 291 days) | 24 | 2 | 1 | -173 / 52 / 90 / 147 | 46 / 0 |
| ATL-LAX-SEA:DL895+DL2640 | LAX | 97% (220 of 226 days) | 4 | 0 | 2 | -58 / 116 / 175 / 223 | 75 / 0 |
| ATL-LAX-SEA:DL898+DL1045 | LAX | 82% (263 of 320 days) | 51 | 3 | 3 | -140 / 32 / 81 / 143 | 45 / 0 |
| ATL-LAX-SEA:DL898+DL2606 | LAX | 98% (335 of 342 days) | 3 | 2 | 2 | -34 / 118 / 186 / 235 | 23 / 0 |
| ATL-LAX-SEA:DL996+DL1045 | LAX | 97% (316 of 326 days) | 3 | 4 | 3 | -40 / 107 / 157 / 219 | 2 / 0 |
| ATL-LAX-SFO:DL500+DL2986 | LAX | 85% (195 of 229 days) | 29 | 3 | 2 | -113 / 38 / 99 / 183 | 135 / 0 |
| ATL-LAX-SFO:DL501+DL2267 | LAX | 88% (225 of 255 days) | 30 | 0 | 0 | -252 / 38 / 119 / 197 | 110 / 0 |
| ATL-LAX-SFO:DL753+DL2054 | LAX | 96% (270 of 281 days) | 7 | 4 | 0 | -126 / 106 / 140 / 240 | 56 / 0 |
| ATL-LAX-SFO:DL895+DL1559 | LAX | 92% (224 of 243 days) | 17 | 1 | 1 | -165 / 55 / 108 / 185 | 58 / 0 |
| ATL-LAX-SFO:DL898+DL2267 | LAX | 96% (288 of 299 days) | 7 | 1 | 3 | -112 / 97 / 163 / 253 | 66 / 0 |
| ATL-LAX-SFO:DL996+DL2272 | LAX | 92% (289 of 313 days) | 17 | 4 | 3 | -130 / 60 / 101 / 167 | 15 / 0 |
| ATL-LAX-SMF:DL501+DL3759 | LAX | 97% (288 of 297 days) | 5 | 4 | 0 | -322 / 133 / 178 / 228 | 68 / 0 |
| ATL-LAX-SMF:DL501+DL3812 | LAX | 69% (171 of 249 days) | 75 | 3 | 0 | -315 / 27 / 57 / 99 | 116 / 0 |
| ATL-LAX-SMF:DL673+DL3759 | LAX | 98% (222 of 226 days) | 3 | 1 | 0 | -487 / 94 / 132 / 205 | 0 / 0 |
| ATL-LAX-SMF:DL753+DL3712 | LAX | 89% (246 of 276 days) | 28 | 2 | 0 | -256 / 42 / 93 / 153 | 61 / 0 |
| ATL-LAX-SMF:DL895+DL3712 | LAX | 98% (227 of 231 days) | 2 | 1 | 1 | -70 / 112 / 165 / 207 | 70 / 0 |
| ATL-LAX-SMF:DL898+DL3812 | LAX | 96% (345 of 359 days) | 10 | 1 | 3 | -63 / 86 / 137 / 208 | 6 / 0 |
| ATL-LAX-SMF:DL996+DL3812 | LAX | 98% (222 of 226 days) | 1 | 1 | 2 | 6 / 164 / 203 / 253 | 102 / 0 |
| ATL-ORD-SEA:UA516+UA2211 | ORD | 97% (266 of 273 days) | 5 | 2 | 0 | -176 / 164 / 192 / 229 | 67 / 0 |
| BNA-ATL-DEN:DL1155+DL519 | ATL | 93% (269 of 290 days) | 11 | 5 | 5 | -273 / 68 / 188 / 245 | 13 / 0 |
| BNA-ATL-DEN:DL3001+DL706 | ATL | 93% (207 of 222 days) | 11 | 4 | 0 | 21 / 75 / 137 / 209 | 121 / 0 |
| BNA-ATL-DEN:DL3069+DL530 | ATL | 95% (246 of 258 days) | 7 | 5 | 0 | -32 / 97 / 153 / 197 | 56 / 0 |
| BNA-ATL-DEN:DL3142+DL493 | ATL | 93% (232 of 249 days) | 6 | 8 | 3 | -28 / 104 / 162 / 200 | 69 / 0 |
| BNA-ATL-DEN:DL3159+DL746 | ATL | 95% (314 of 329 days) | 9 | 6 | 0 | -29 / 84 / 122 / 189 | 12 / 0 |
| BNA-DFW-DEN:AA1100+AA2235 | DFW | 75% (165 of 220 days) | 41 | 11 | 3 | -225 / 14 / 81 / 141 | 122 / 0 |
| BNA-DFW-DEN:AA1100+AA577 | DFW | 91% (309 of 338 days) | 14 | 14 | 1 | -118 / 120 / 187 / 242 | 4 / 0 |
| BNA-DFW-DEN:AA2238+AA662 | DFW | 74% (182 of 246 days) | 40 | 24 | 0 | -805 / 16 / 79 / 141 | 0 / 0 |
| BNA-DFW-DEN:AA2244+AA577 | DFW | 76% (270 of 354 days) | 62 | 19 | 3 | -1185 / 14 / 86 / 129 | 0 / 0 |
| BNA-DFW-DEN:AA2244+AA662 | DFW | 90% (219 of 243 days) | 8 | 15 | 1 | -1101 / 114 / 201 / 273 | 111 / 0 |
| BNA-DFW-DEN:AA2787+AA2359 | DFW | 93% (205 of 221 days) | 4 | 12 | 0 | -329 / 98 / 180 / 209 | 123 / 0 |
| BNA-ORD-DEN:UA5741+UA1803 | ORD | 90% (220 of 245 days) | 17 | 8 | 0 | -246 / 53 / 164 / 193 | 89 / 0 |
| BOS-ATL-SFO:DL376+DL517 | ATL | 96% (242 of 253 days) | 7 | 4 | 0 | -448 / 83 / 152 / 206 | 108 / 0 |
| BOS-ATL-SFO:DL695+DL531 | ATL | 97% (333 of 344 days) | 5 | 6 | 0 | -106 / 111 / 146 / 222 | 20 / 0 |
| BOS-ATL-SFO:DL973+DL823 | ATL | 96% (334 of 347 days) | 7 | 5 | 1 | -220 / 90 / 135 / 203 | 11 / 0 |
| BOS-DEN-SFO:UA414+UA1007 | DEN | 98% (315 of 321 days) | 2 | 3 | 1 | -6 / 184 / 223 / 283 | 31 / 0 |
| BOS-DEN-SFO:UA647+UA1561 | DEN | 97% (328 of 339 days) | 7 | 4 | 0 | -258 / 73 / 98 / 139 | 24 / 0 |
| BOS-DEN-SFO:UA647+UA1812 | DEN | 99% (298 of 302 days) | 1 | 3 | 0 | -128 / 196 / 224 / 260 | 61 / 0 |
| BOS-DEN-SFO:UA662+UA1812 | DEN | 96% (287 of 299 days) | 10 | 1 | 1 | -168 / 75 / 101 / 136 | 46 / 0 |
| BOS-LAX-SFO:DL479+DL2267 | LAX | 95% (254 of 266 days) | 10 | 2 | 0 | -60 / 105 / 162 / 246 | 99 / 0 |
| BOS-LAX-SFO:UA333+UA1597 | LAX | 72% (217 of 301 days) | 80 | 2 | 2 | -927 / 15 / 62 / 106 | 46 / 0 |
| BOS-ORD-SFO:UA1414+UA1387 | ORD | 88% (210 of 240 days) | 26 | 4 | 0 | -143 / 44 / 62 / 91 | 69 / 0 |
| BOS-ORD-SFO:UA1414+UA343 | ORD | 97% (277 of 286 days) | 1 | 7 | 1 | -129 / 152 / 173 / 202 | 23 / 0 |
| BOS-PHX-SFO:AA1057+AA2421 | PHX | 89% (209 of 234 days) | 25 | 0 | 0 | -2505 / 44 / 94 / 155 | 128 / 0 |
| CLE-ATL-SFO:DL1369+DL823 | ATL | 97% (226 of 234 days) | 3 | 5 | 0 | -499 / 124 / 197 / 232 | 8 / 0 |
| CLE-ATL-SFO:DL2734+DL531 | ATL | 97% (292 of 302 days) | 7 | 3 | 0 | -303 / 133 / 166 / 245 | 52 / 0 |
| CLE-ATL-SFO:DL2838+DL531 | ATL | 91% (290 of 317 days) | 21 | 6 | 0 | -504 / 61 / 110 / 201 | 24 / 0 |
| CLE-DEN-SFO:UA1690+UA1561 | DEN | 94% (286 of 304 days) | 18 | 0 | 0 | -372 / 57 / 89 / 185 | 24 / 0 |
| CLE-DEN-SFO:UA1690+UA1812 | DEN | 99% (225 of 228 days) | 2 | 1 | 0 | -243 / 177 / 210 / 238 | 100 / 0 |
| CLE-DEN-SFO:UA486+UA2681 | DEN | 91% (213 of 235 days) | 18 | 3 | 1 | -32 / 48 / 77 / 133 | 37 / 0 |
| CLE-ORD-SFO:UA2465+UA1878 | ORD | 97% (216 of 222 days) | 4 | 1 | 1 | -207 / 184 / 206 / 230 | 0 / 0 |
| CLE-ORD-SFO:UA398+UA1387 | ORD | 86% (192 of 222 days) | 29 | 1 | 0 | -82 / 42 / 72 / 104 | 69 / 0 |
| CLE-ORD-SFO:UA398+UA343 | ORD | 99% (264 of 268 days) | 1 | 2 | 1 | 19 / 152 / 189 / 220 | 23 / 0 |
| CLE-ORD-SFO:UA609+UA1577 | ORD | 99% (221 of 224 days) | 2 | 1 | 0 | -44 / 153 / 184 / 214 | 56 / 0 |
| CLE-ORD-SFO:UA609+UA1878 | ORD | 90% (253 of 280 days) | 24 | 2 | 1 | -83 / 47 / 84 / 118 | 0 / 0 |
| DEN-LAX-HNL:DL2828+DL443 | LAX | 98% (217 of 221 days) | 1 | 3 | 0 | -188 / 184 / 229 / 262 | 23 / 0 |
| DEN-LAX-HNL:UA1093+UA1158 | LAX | 93% (230 of 247 days) | 14 | 1 | 2 | 23 / 53 / 72 / 97 | 87 / 0 |
| DEN-LAX-HNL:UA1252+UA1170 | LAX | 98% (277 of 283 days) | 5 | 1 | 0 | -92 / 109 / 138 / 167 | 0 / 0 |
| DEN-LAX-HNL:UA405+UA1431 | LAX | 97% (228 of 234 days) | 5 | 1 | 0 | -71 / 88 / 109 / 142 | 89 / 0 |
| DEN-PHX-HNL:AA1404+AA692 | PHX | 93% (240 of 259 days) | 15 | 3 | 1 | -1810 / 68 / 107 / 160 | 98 / 0 |
| DEN-SFO-HNL:UA1561+UA1509 | SFO | 98% (334 of 341 days) | 6 | 0 | 1 | -246 / 173 / 211 / 248 | 0 / 0 |
| DEN-SFO-HNL:UA1812+UA1509 | SFO | 91% (278 of 304 days) | 26 | 0 | 0 | -155 / 51 / 89 / 126 | 0 / 0 |
| DEN-SFO-HNL:UA1812+UA638 | SFO | 98% (241 of 245 days) | 4 | 0 | 0 | -52 / 169 / 229 / 260 | 59 / 0 |
| DEN-SFO-HNL:UA2041+UA300 | SFO | 98% (274 of 280 days) | 4 | 1 | 1 | -10 / 81 / 125 / 166 | 3 / 0 |
| DEN-SFO-HNL:UA573+UA1175 | SFO | 93% (249 of 267 days) | 13 | 4 | 1 | -234 / 75 / 122 / 169 | 0 / 0 |
| EWR-ATL-MKE:DL1673+DL1246 | ATL | 91% (263 of 289 days) | 14 | 12 | 0 | -224 / 58 / 196 / 228 | 30 / 0 |
| EWR-ATL-MKE:DL2312+DL1268 | ATL | 83% (253 of 306 days) | 38 | 14 | 1 | -864 / 25 / 137 / 187 | 30 / 0 |
| EWR-ATL-MKE:DL2325+DL2152 | ATL | 88% (210 of 239 days) | 24 | 5 | 0 | -579 / 43 / 123 / 165 | 97 / 0 |
| EWR-ATL-MKE:DL2340+DL1268 | ATL | 53% (120 of 225 days) | 94 | 10 | 1 | -907 / -62 / 54 / 97 | 1 / 0 |
| EWR-ATL-MKE:DL2365+DL1246 | ATL | 94% (237 of 251 days) | 10 | 4 | 0 | -226 / 104 / 148 / 173 | 110 / 0 |
| EWR-ATL-MKE:DL2397+DL1173 | ATL | 94% (240 of 254 days) | 8 | 6 | 0 | -55 / 93 / 136 / 208 | 98 / 0 |
| EWR-ORD-MKE:UA1144+UA5320 | ORD | 94% (246 of 262 days) | 12 | 4 | 0 | -103 / 116 / 175 / 236 | 3 / 0 |
| EWR-ORD-MKE:UA1144+UA5555 | ORD | 79% (209 of 265 days) | 53 | 3 | 0 | -203 / 11 / 66 / 139 | 0 / 0 |
| EWR-ORD-MKE:UA1525+UA5668 | ORD | 97% (217 of 224 days) | 5 | 2 | 0 | -60 / 110 / 142 / 173 | 141 / 0 |
| EWR-ORD-MKE:UA2100+UA5234 | ORD | 88% (211 of 239 days) | 26 | 2 | 0 | -134 / 42 / 73 / 143 | 126 / 0 |
| EWR-ORD-MKE:UA254+UA5262 | ORD | 57% (159 of 279 days) | 103 | 14 | 3 | -276 / -2 / 52 / 98 | 17 / 0 |
| EWR-ORD-MKE:UA661+UA5262 | ORD | 94% (218 of 233 days) | 11 | 4 | 0 | -320 / 90 / 146 / 196 | 35 / 0 |
| EWR-ORD-MKE:UA661+UA5320 | ORD | 69% (164 of 239 days) | 73 | 2 | 0 | -443 / -4 / 55 / 105 | 29 / 0 |
| IND-ATL-SFO:DL2952+DL823 | ATL | 95% (225 of 237 days) | 7 | 5 | 0 | -5 / 75 / 119 / 179 | 3 / 0 |
| IND-ATL-SFO:DL3105+DL531 | ATL | 96% (286 of 297 days) | 5 | 6 | 0 | -836 / 159 / 184 / 257 | 67 / 0 |
| IND-ATL-SFO:DL3106+DL531 | ATL | 93% (280 of 302 days) | 15 | 7 | 0 | -694 / 55 / 117 / 195 | 27 / 0 |
| IND-ATL-SFO:DL3125+DL823 | ATL | 98% (235 of 241 days) | 3 | 2 | 1 | -629 / 192 / 222 / 268 | 55 / 0 |
| IND-DEN-SFO:UA1607+UA1561 | DEN | 98% (334 of 341 days) | 2 | 5 | 0 | -17 / 81 / 115 / 185 | 24 / 0 |
| IND-LAX-SFO:DL861+DL2272 | LAX | 96% (280 of 291 days) | 7 | 3 | 1 | -178 / 68 / 118 / 201 | 1 / 0 |
| IND-ORD-SFO:UA3479+UA1387 | ORD | 99% (241 of 243 days) | 0 | 2 | 0 | 102 / 143 / 169 / 190 | 118 / 0 |
| IND-ORD-SFO:UA3483+UA1387 | ORD | 92% (223 of 242 days) | 17 | 2 | 0 | -38 / 48 / 65 / 90 | 69 / 0 |
| IND-ORD-SFO:UA3483+UA343 | ORD | 99% (289 of 293 days) | 0 | 3 | 1 | 76 / 154 / 174 / 210 | 18 / 0 |
| IND-ORD-SFO:UA3565+UA1878 | ORD | 98% (313 of 319 days) | 1 | 4 | 1 | -130 / 177 / 207 / 239 | 0 / 0 |
| IND-ORD-SFO:UA3565+UA343 | ORD | 93% (274 of 296 days) | 14 | 6 | 2 | -256 / 55 / 80 / 112 | 23 / 0 |
| IND-ORD-SFO:UA3677+UA1577 | ORD | 98% (238 of 242 days) | 1 | 3 | 0 | 7 / 160 / 182 / 210 | 100 / 0 |
| IND-ORD-SFO:UA3677+UA1878 | ORD | 95% (324 of 342 days) | 14 | 3 | 1 | -181 / 56 / 80 / 111 | 0 / 0 |
| LAX-ATL-IAD:DL390+DL1695 | ATL | 87% (298 of 344 days) | 36 | 7 | 3 | -251 / 42 / 93 / 178 | 21 / 0 |
| LAX-ATL-IAD:DL395+DL2549 | ATL | 89% (292 of 327 days) | 23 | 11 | 1 | -370 / 58 / 119 / 209 | 31 / 0 |
| LAX-ATL-IAD:DL515+DL2902 | ATL | 86% (220 of 256 days) | 32 | 3 | 1 | -331 / 37 / 97 / 205 | 108 / 0 |
| LAX-ATL-IAD:DL715+DL2549 | ATL | 76% (173 of 227 days) | 45 | 7 | 2 | -411 / 28 / 60 / 119 | 138 / 0 |
| LAX-DEN-IAD:UA1260+UA2408 | DEN | 97% (346 of 357 days) | 4 | 6 | 1 | -217 / 154 / 207 / 243 | 1 / 0 |
| LAX-DEN-IAD:UA1260+UA798 | DEN | 93% (314 of 336 days) | 18 | 4 | 0 | -346 / 71 / 97 / 150 | 22 / 0 |
| LAX-DEN-IAD:UA1339+UA2087 | DEN | 96% (313 of 327 days) | 5 | 7 | 2 | 7 / 87 / 126 / 151 | 38 / 0 |
| LAX-DEN-IAD:UA1912+UA347 | DEN | 92% (210 of 229 days) | 15 | 3 | 1 | -83 / 63 / 91 / 119 | 62 / 0 |
| LAX-DEN-IAD:UA1912+UA798 | DEN | 99% (289 of 291 days) | 0 | 2 | 0 | 67 / 197 / 228 / 275 | 0 / 0 |
| LAX-DFW-IAD:AA2811+AA1863 | DFW | 93% (219 of 235 days) | 9 | 5 | 2 | -539 / 68 / 95 / 149 | 101 / 0 |
| LGA-ATL-MCO:DL342+DL1030 | ATL | 96% (333 of 347 days) | 2 | 12 | 0 | 16 / 97 / 126 / 157 | 0 / 0 |
| LGA-ATL-MCO:DL342+DL1576 | ATL | 97% (335 of 346 days) | 0 | 9 | 2 | 94 / 167 / 203 / 244 | 1 / 0 |
| LGA-ATL-MCO:DL342+DL664 | ATL | 77% (247 of 321 days) | 62 | 9 | 3 | -92 / 34 / 64 / 102 | 26 / 0 |
| LGA-ATL-MCO:DL364+DL1030 | ATL | 85% (247 of 291 days) | 35 | 9 | 0 | -270 / 42 / 70 / 100 | 0 / 0 |
| LGA-ATL-MCO:DL364+DL1372 | ATL | 96% (279 of 290 days) | 2 | 9 | 0 | -157 / 173 / 221 / 263 | 1 / 0 |
| LGA-ATL-MCO:DL364+DL1576 | ATL | 96% (277 of 290 days) | 6 | 6 | 1 | -228 / 110 / 149 / 180 | 1 / 0 |
| LGA-ATL-MCO:DL550+DL1030 | ATL | 97% (353 of 365 days) | 1 | 11 | 0 | -24 / 164 / 191 / 223 | 0 / 0 |
| LGA-ATL-MCO:DL550+DL1658 | ATL | 83% (304 of 365 days) | 52 | 9 | 0 | -161 / 36 / 64 / 98 | 0 / 0 |
| LGA-ATL-MCO:DL550+DL664 | ATL | 96% (349 of 365 days) | 5 | 9 | 2 | -93 / 98 / 127 / 170 | 0 / 0 |
| LGA-ATL-MCO:DL968+DL1162 | ATL | 93% (252 of 271 days) | 8 | 11 | 0 | -177 / 116 / 180 / 235 | 52 / 0 |
| LGA-ATL-MCO:DL968+DL1733 | ATL | 88% (275 of 313 days) | 28 | 9 | 1 | -244 / 52 / 110 / 156 | 10 / 0 |
| LGA-ATL-MCO:DL969+DL1733 | ATL | 85% (218 of 255 days) | 32 | 5 | 0 | -279 / 34 / 159 / 198 | 9 / 0 |
| LGA-ATL-MCO:DL970+DL1162 | ATL | 76% (184 of 243 days) | 48 | 10 | 1 | -680 / 23 / 70 / 118 | 85 / 0 |
| LGA-ATL-MCO:DL974+DL1733 | ATL | 97% (248 of 256 days) | 3 | 5 | 0 | -95 / 180 / 230 / 278 | 58 / 0 |
| LGA-ATL-MCO:DL974+DL2035 | ATL | 67% (205 of 305 days) | 93 | 5 | 2 | -250 / 8 / 59 / 134 | 9 / 0 |
| LGA-ATL-MCO:DL974+DL2881 | ATL | 93% (274 of 294 days) | 13 | 5 | 2 | -210 / 86 / 133 / 187 | 20 / 0 |
| LGA-ATL-MCO:DL988+DL1497 | ATL | 72% (209 of 289 days) | 70 | 7 | 3 | -403 / 16 / 64 / 128 | 44 / 0 |
| LGA-ATL-MCO:DL988+DL2035 | ATL | 92% (271 of 296 days) | 15 | 6 | 4 | -227 / 75 / 126 / 191 | 37 / 0 |
| LGA-ATL-MCO:DL988+DL2881 | ATL | 95% (276 of 290 days) | 5 | 7 | 2 | -182 / 151 / 203 / 262 | 43 / 0 |
| LGA-ATL-MCO:DL989+DL1150 | ATL | 95% (271 of 285 days) | 7 | 6 | 1 | -235 / 104 / 161 / 220 | 0 / 0 |
| LGA-ATL-MCO:DL989+DL1372 | ATL | 88% (250 of 285 days) | 30 | 5 | 0 | -377 / 42 / 99 / 141 | 0 / 0 |
| LGA-ATL-MCO:DL989+DL1742 | ATL | 97% (276 of 284 days) | 1 | 6 | 1 | -232 / 166 / 227 / 285 | 1 / 0 |
| LGA-ATL-MCO:DL990+DL1497 | ATL | 97% (305 of 315 days) | 1 | 5 | 4 | -68 / 127 / 181 / 251 | 8 / 0 |
| LGA-ATL-MCO:DL990+DL1742 | ATL | 90% (291 of 322 days) | 23 | 5 | 3 | -163 / 50 / 106 / 167 | 1 / 0 |
| LGA-ATL-MCO:DL990+DL2035 | ATL | 96% (238 of 247 days) | 1 | 3 | 5 | 6 / 199 / 236 / 325 | 76 / 0 |
| LGA-ATL-MCO:DL992+DL1150 | ATL | 96% (344 of 358 days) | 6 | 7 | 1 | -483 / 172 / 213 / 269 | 4 / 0 |
| LGA-ATL-MCO:DL992+DL1372 | ATL | 95% (342 of 361 days) | 12 | 7 | 0 | -534 / 104 / 150 / 198 | 1 / 0 |
| LGA-ATL-MCO:DL992+DL1576 | ATL | 87% (309 of 356 days) | 42 | 4 | 1 | -616 / 41 / 82 / 120 | 6 / 0 |
| LGA-ATL-MCO:DL993+DL1150 | ATL | 91% (325 of 359 days) | 25 | 8 | 1 | -219 / 50 / 102 / 163 | 0 / 0 |
| LGA-ATL-MCO:DL993+DL1497 | ATL | 95% (287 of 302 days) | 3 | 8 | 4 | -82 / 193 / 237 / 305 | 57 / 0 |
| LGA-ATL-MCO:DL993+DL1742 | ATL | 95% (341 of 358 days) | 7 | 8 | 2 | -159 / 114 / 167 / 223 | 1 / 0 |
| LGA-ATL-MCO:DL994+DL1497 | ATL | 93% (291 of 314 days) | 15 | 5 | 3 | -415 / 66 / 118 / 174 | 10 / 0 |
| LGA-ATL-MCO:DL994+DL2035 | ATL | 96% (301 of 315 days) | 7 | 4 | 3 | -351 / 140 / 181 / 244 | 9 / 0 |
| LGA-ORD-MCO:UA1310+UA2042 | ORD | 95% (273 of 288 days) | 11 | 2 | 2 | -488 / 110 / 146 / 174 | 76 / 0 |
| LGA-ORD-MCO:UA2389+UA2323 | ORD | 92% (308 of 334 days) | 19 | 5 | 2 | -33 / 49 / 76 / 105 | 31 / 0 |
| LGA-ORD-MCO:UA623+UA2042 | ORD | 96% (210 of 219 days) | 4 | 4 | 1 | -215 / 182 / 209 / 240 | 53 / 0 |
| MCO-ATL-LAX:DL1030+DL301 | ATL | 89% (242 of 272 days) | 25 | 3 | 2 | -215 / 50 / 87 / 133 | 22 / 0 |
| MCO-ATL-LAX:DL1030+DL500 | ATL | 94% (263 of 279 days) | 9 | 3 | 4 | -119 / 124 / 182 / 224 | 15 / 0 |
| MCO-ATL-LAX:DL1150+DL331 | ATL | 81% (200 of 247 days) | 35 | 12 | 0 | -203 / 12 / 123 / 193 | 69 / 0 |
| MCO-ATL-LAX:DL1213+DL753 | ATL | 92% (311 of 337 days) | 20 | 6 | 0 | -447 / 60 / 101 / 149 | 28 / 0 |
| MCO-ATL-LAX:DL1372+DL319 | ATL | 86% (219 of 255 days) | 26 | 8 | 2 | -138 / 43 / 117 / 177 | 72 / 0 |
| MCO-ATL-LAX:DL1372+DL331 | ATL | 91% (227 of 250 days) | 11 | 12 | 0 | -110 / 101 / 190 / 251 | 77 / 0 |
| MCO-ATL-LAX:DL1446+DL501 | ATL | 96% (345 of 359 days) | 6 | 8 | 0 | -238 / 75 / 107 / 143 | 0 / 0 |
| MCO-ATL-LAX:DL1446+DL673 | ATL | 97% (213 of 220 days) | 1 | 6 | 0 | -140 / 148 / 171 / 210 | 139 / 0 |
| MCO-ATL-LAX:DL1463+DL501 | ATL | 78% (210 of 269 days) | 53 | 6 | 0 | -181 / 24 / 59 / 91 | 90 / 0 |
| MCO-ATL-LAX:DL1463+DL673 | ATL | 96% (211 of 220 days) | 5 | 4 | 0 | -77 / 97 / 119 / 155 | 139 / 0 |
| MCO-ATL-LAX:DL1463+DL895 | ATL | 98% (256 of 262 days) | 2 | 3 | 1 | -103 / 148 / 198 / 242 | 97 / 0 |
| MCO-ATL-LAX:DL1494+DL501 | ATL | 97% (355 of 365 days) | 3 | 7 | 0 | -140 / 132 / 161 / 197 | 0 / 0 |
| MCO-ATL-LAX:DL1494+DL898 | ATL | 86% (250 of 291 days) | 36 | 4 | 1 | -245 / 42 / 74 / 114 | 74 / 0 |
| MCO-ATL-LAX:DL1505+DL673 | ATL | 76% (172 of 226 days) | 49 | 5 | 0 | -245 / 35 / 58 / 94 | 139 / 0 |
| MCO-ATL-LAX:DL1505+DL753 | ATL | 95% (279 of 293 days) | 6 | 8 | 0 | -552 / 197 / 222 / 254 | 72 / 0 |
| MCO-ATL-LAX:DL1505+DL895 | ATL | 94% (249 of 264 days) | 7 | 7 | 1 | -612 / 71 / 140 / 178 | 101 / 0 |
| MCO-ATL-LAX:DL1548+DL501 | ATL | 96% (324 of 336 days) | 3 | 9 | 0 | -74 / 187 / 214 / 248 | 0 / 0 |
| MCO-ATL-LAX:DL1548+DL898 | ATL | 94% (317 of 336 days) | 7 | 9 | 3 | -194 / 75 / 121 / 156 | 0 / 0 |
| MCO-ATL-LAX:DL1576+DL319 | ATL | 92% (235 of 255 days) | 10 | 9 | 1 | -281 / 115 / 196 / 246 | 77 / 0 |
| MCO-ATL-LAX:DL1576+DL500 | ATL | 79% (262 of 331 days) | 59 | 7 | 3 | -422 / 17 / 114 / 170 | 1 / 0 |
| MCO-ATL-LAX:DL1658+DL301 | ATL | 96% (277 of 289 days) | 7 | 5 | 0 | -600 / 148 / 207 / 250 | 6 / 0 |
| MCO-ATL-LAX:DL1658+DL753 | ATL | 60% (133 of 220 days) | 83 | 4 | 0 | -761 / 5 / 49 / 89 | 75 / 0 |
| MCO-ATL-LAX:DL2204+DL753 | ATL | 96% (323 of 337 days) | 7 | 7 | 0 | -150 / 131 / 167 / 210 | 28 / 0 |
| MCO-ATL-LAX:DL2204+DL895 | ATL | 91% (256 of 282 days) | 20 | 5 | 1 | -290 / 60 / 86 / 220 | 83 / 0 |
| MCO-ATL-LAX:DL664+DL301 | ATL | 91% (275 of 301 days) | 22 | 3 | 1 | -339 / 61 / 144 / 194 | 64 / 0 |
| MCO-ATL-LGA:DL1030+DL434 | ATL | 95% (253 of 265 days) | 6 | 3 | 3 | -157 / 129 / 177 / 236 | 29 / 0 |
| MCO-ATL-LGA:DL1030+DL468 | ATL | 96% (273 of 285 days) | 4 | 6 | 2 | -50 / 155 / 235 / 284 | 9 / 0 |
| MCO-ATL-LGA:DL1150+DL520 | ATL | 88% (225 of 257 days) | 24 | 7 | 1 | -190 / 46 / 125 / 182 | 59 / 0 |
| MCO-ATL-LGA:DL1213+DL433 | ATL | 95% (332 of 351 days) | 9 | 10 | 0 | -387 / 126 / 180 / 233 | 14 / 0 |
| MCO-ATL-LGA:DL1213+DL460 | ATL | 76% (256 of 336 days) | 71 | 6 | 3 | -490 / 21 / 64 / 111 | 29 / 0 |
| MCO-ATL-LGA:DL1372+DL468 | ATL | 70% (203 of 289 days) | 76 | 10 | 0 | -236 / 8 / 99 / 138 | 38 / 0 |
| MCO-ATL-LGA:DL1372+DL490 | ATL | 88% (263 of 298 days) | 20 | 14 | 1 | -202 / 67 / 149 / 194 | 29 / 0 |
| MCO-ATL-LGA:DL1372+DL520 | ATL | 95% (245 of 258 days) | 4 | 7 | 2 | -79 / 133 / 215 / 251 | 69 / 0 |
| MCO-ATL-LGA:DL1446+DL371 | ATL | 96% (341 of 354 days) | 4 | 8 | 1 | -214 / 95 / 117 / 145 | 5 / 0 |
| MCO-ATL-LGA:DL1446+DL467 | ATL | 97% (285 of 295 days) | 3 | 7 | 0 | -192 / 154 / 177 / 206 | 64 / 0 |
| MCO-ATL-LGA:DL1446+DL525 | ATL | 97% (322 of 333 days) | 2 | 8 | 1 | -107 / 216 / 237 / 271 | 26 / 0 |
| MCO-ATL-LGA:DL1446+DL557 | ATL | 73% (220 of 303 days) | 75 | 7 | 1 | -305 / 31 / 55 / 85 | 56 / 0 |
| MCO-ATL-LGA:DL1463+DL371 | ATL | 82% (292 of 354 days) | 53 | 8 | 1 | -161 / 29 / 63 / 87 | 5 / 0 |
| MCO-ATL-LGA:DL1463+DL460 | ATL | 97% (311 of 319 days) | 1 | 5 | 2 | 8 / 212 / 246 / 284 | 40 / 0 |
| MCO-ATL-LGA:DL1463+DL467 | ATL | 96% (289 of 300 days) | 6 | 5 | 0 | -88 / 83 / 123 / 150 | 59 / 0 |
| MCO-ATL-LGA:DL1463+DL525 | ATL | 97% (324 of 333 days) | 2 | 5 | 2 | -26 / 158 / 183 / 220 | 26 / 0 |
| MCO-ATL-LGA:DL1494+DL371 | ATL | 96% (347 of 360 days) | 3 | 9 | 1 | -68 / 151 / 170 / 198 | 5 / 0 |
| MCO-ATL-LGA:DL1494+DL467 | ATL | 97% (276 of 284 days) | 1 | 7 | 0 | 20 / 208 / 229 / 261 | 81 / 0 |
| MCO-ATL-LGA:DL1494+DL513 | ATL | 61% (209 of 344 days) | 127 | 8 | 0 | -291 / 30 / 48 / 63 | 21 / 0 |
| MCO-ATL-LGA:DL1494+DL557 | ATL | 96% (299 of 312 days) | 6 | 6 | 1 | -50 / 90 / 109 / 139 | 53 / 0 |
| MCO-ATL-LGA:DL1505+DL460 | ATL | 95% (318 of 334 days) | 5 | 8 | 3 | -579 / 159 / 184 / 227 | 31 / 0 |
| MCO-ATL-LGA:DL1505+DL467 | ATL | 83% (249 of 300 days) | 44 | 7 | 0 | -703 / 36 / 62 / 94 | 65 / 0 |
| MCO-ATL-LGA:DL1505+DL525 | ATL | 95% (321 of 339 days) | 8 | 8 | 2 | -644 / 99 / 123 / 157 | 26 / 0 |
| MCO-ATL-LGA:DL1548+DL371 | ATL | 96% (318 of 331 days) | 3 | 9 | 1 | -64 / 207 / 222 / 251 | 5 / 0 |
| MCO-ATL-LGA:DL1548+DL513 | ATL | 95% (315 of 331 days) | 6 | 10 | 0 | -207 / 85 / 100 / 114 | 5 / 0 |
| MCO-ATL-LGA:DL1548+DL557 | ATL | 97% (280 of 289 days) | 2 | 6 | 1 | -117 / 146 / 160 / 186 | 47 / 0 |
| MCO-ATL-LGA:DL1576+DL434 | ATL | 87% (259 of 299 days) | 30 | 7 | 3 | -430 / 44 / 111 / 164 | 33 / 0 |
| MCO-ATL-LGA:DL1576+DL468 | ATL | 92% (292 of 318 days) | 14 | 11 | 1 | -371 / 89 / 171 / 225 | 14 / 0 |
| MCO-ATL-LGA:DL1576+DL490 | ATL | 92% (287 of 312 days) | 10 | 14 | 1 | -362 / 119 / 227 / 276 | 20 / 0 |
| MCO-ATL-LGA:DL1658+DL433 | ATL | 91% (264 of 291 days) | 19 | 8 | 0 | -675 / 63 / 116 / 172 | 4 / 0 |
| MCO-ATL-LGA:DL1658+DL524 | ATL | 91% (232 of 255 days) | 17 | 5 | 1 | -565 / 58 / 193 / 230 | 40 / 0 |
| MCO-ATL-LGA:DL2204+DL433 | ATL | 96% (227 of 237 days) | 4 | 6 | 0 | -155 / 192 / 238 / 292 | 128 / 0 |
| MCO-ATL-LGA:DL2204+DL460 | ATL | 93% (314 of 336 days) | 13 | 6 | 3 | -227 / 95 / 126 / 172 | 29 / 0 |
| MCO-ATL-LGA:DL2204+DL525 | ATL | 84% (286 of 339 days) | 45 | 6 | 2 | -278 / 37 / 65 / 100 | 26 / 0 |
| MCO-ATL-LGA:DL664+DL433 | ATL | 66% (174 of 265 days) | 84 | 7 | 0 | -282 / 3 / 58 / 115 | 100 / 0 |
| MCO-ATL-LGA:DL664+DL434 | ATL | 96% (237 of 248 days) | 6 | 3 | 2 | -236 / 174 / 236 / 279 | 117 / 0 |
| MCO-DEN-LAX:UA1520+UA2240 | DEN | 96% (323 of 336 days) | 7 | 5 | 1 | -462 / 155 / 192 / 239 | 7 / 0 |
| MCO-DEN-LAX:UA1520+UA564 | DEN | 85% (229 of 269 days) | 33 | 6 | 1 | -590 / 40 / 88 / 142 | 74 / 0 |
| MCO-ORD-LGA:UA1828+UA1576 | ORD | 82% (199 of 244 days) | 40 | 4 | 1 | -793 / 19 / 87 / 150 | 121 / 0 |
| SAN-ATL-IAD:DL725+DL1309 | ATL | 85% (218 of 257 days) | 32 | 4 | 3 | -120 / 40 / 79 / 130 | 108 / 0 |
| SAN-ATL-IAD:DL729+DL1695 | ATL | 93% (268 of 289 days) | 17 | 2 | 2 | -443 / 55 / 94 / 168 | 76 / 0 |
| SAN-ATL-IAD:DL762+DL2902 | ATL | 92% (232 of 253 days) | 15 | 5 | 1 | -616 / 70 / 120 / 236 | 83 / 0 |
| SAN-DEN-IAD:UA1374+UA2408 | DEN | 95% (229 of 242 days) | 12 | 0 | 1 | -53 / 77 / 112 / 145 | 0 / 0 |
| SAN-DEN-IAD:UA2476+UA347 | DEN | 93% (245 of 263 days) | 17 | 1 | 0 | -357 / 55 / 93 / 136 | 62 / 0 |
| SAN-DEN-IAD:UA2476+UA798 | DEN | 98% (302 of 309 days) | 3 | 4 | 0 | -186 / 192 / 233 / 284 | 16 / 0 |
| SAN-DEN-IAD:UA264+UA2408 | DEN | 97% (266 of 275 days) | 5 | 3 | 1 | -75 / 136 / 203 / 243 | 0 / 0 |
| SAN-DEN-IAD:UA264+UA798 | DEN | 84% (230 of 275 days) | 44 | 0 | 1 | -202 / 32 / 87 / 125 | 0 / 0 |
| SAN-DFW-IAD:AA2535+AA1863 | DFW | 91% (214 of 235 days) | 12 | 8 | 1 | -514 / 58 / 79 / 140 | 126 / 0 |
| SAN-LAX-IAD:UA4723+UA1140 | LAX | 78% (175 of 225 days) | 44 | 4 | 2 | -355 / 36 / 66 / 119 | 139 / 0 |
| SAN-LAX-IAD:UA4723+UA2667 | LAX | 97% (335 of 345 days) | 7 | 0 | 3 | -313 / 147 / 174 / 223 | 19 / 0 |
| SAN-LAX-IAD:UA5249+UA1635 | LAX | 91% (279 of 308 days) | 27 | 1 | 1 | -121 / 48 / 83 / 142 | 52 / 0 |
| SLC-DEN-ATL:UA1790+UA1305 | DEN | 86% (267 of 309 days) | 34 | 4 | 4 | -925 / 43 / 94 / 147 | 45 / 0 |
| SLC-DEN-ATL:UA4720+UA1305 | DEN | 96% (268 of 279 days) | 8 | 2 | 1 | -861 / 142 / 191 / 253 | 45 / 0 |
| SLC-DFW-ATL:AA1214+AA1236 | DFW | 93% (210 of 226 days) | 4 | 9 | 3 | -1679 / 154 / 214 / 267 | 138 / 1 |
| SLC-DFW-ATL:AA2066+AA2403 | DFW | 82% (209 of 255 days) | 36 | 8 | 2 | -981 / 40 / 98 / 257 | 108 / 0 |
| SLC-DFW-ATL:AA2195+AA1248 | DFW | 94% (217 of 232 days) | 3 | 11 | 1 | -80 / 137 / 200 / 260 | 132 / 0 |
| SLC-DFW-ATL:DL2798+DL414 | DFW | 97% (299 of 309 days) | 4 | 5 | 1 | 7 / 91 / 127 / 183 | 0 / 0 |
| SLC-DFW-ATL:DL2800+DL32 | DFW | 95% (259 of 274 days) | 6 | 5 | 4 | -137 / 90 / 152 / 238 | 90 / 0 |
| SLC-DFW-ATL:DL2811+DL436 | DFW | 93% (219 of 235 days) | 10 | 5 | 1 | -115 / 79 / 154 / 223 | 112 / 0 |
| SLC-PHX-ATL:DL1431+DL796 | PHX | 91% (310 of 342 days) | 24 | 6 | 2 | -152 / 54 / 84 / 122 | 23 / 0 |
| SLC-PHX-ATL:DL1447+DL348 | PHX | 96% (235 of 244 days) | 3 | 5 | 1 | -188 / 76 / 99 / 136 | 121 / 0 |

## Attribution

Flight data: U.S. Department of Transportation, Bureau of Transportation Statistics (TranStats): Marketing Carrier On-Time Performance, T-100 Domestic Segment (U.S. Carriers) and the Airline Origin and Destination Survey (DB1B Market). Airport time zones: airportsdata (MIT License, Copyright (c) 2020- Mike Borsetti; includes data Copyright (c) 2014 mwgg). Time-zone rules: tzdata (Apache License 2.0).
