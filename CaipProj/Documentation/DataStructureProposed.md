To predict the **maintenance cost in PKR for a specific house or residential apartment during the next 12 months**, you need historical data that connects each property’s characteristics, condition, usage and previous maintenance activities with its actual maintenance cost.

A practical dataset should use:

> **One row = one house or apartment for one historical 12-month period**

For example, a row containing information available up to December 2024 would have the actual maintenance cost incurred during January–December 2025 as its target.

## 1. Target variable

This is the value the ML model will learn to predict.

| Field                                 | Description                                                  |
| ------------------------------------- | ------------------------------------------------------------ |
| `maintenance_cost_next_12_months_pkr` | Total actual maintenance cost during the following 12 months |

The total should include:

```text
Total cost =
material cost
+ labour cost
+ contractor cost
+ transport cost
+ equipment cost
+ other repair-related cost
```

You should define whether the prediction includes:

* Routine maintenance
* Emergency maintenance
* Major repairs
* Renovation costs
* Appliance maintenance
* Shared building maintenance

For the POC, I recommend including **routine, corrective and emergency building maintenance**, but keeping large renovations or complete reconstruction separate.

---

# 2. Property identification data

Each house or apartment must have a stable identifier.

| Field                       | Example                    |
| --------------------------- | -------------------------- |
| `property_id`               | WAPDA-LHR-B12-H04          |
| `colony_id`                 | LHR-COL-01                 |
| `colony_name`               | WAPDA Staff Colony Lahore  |
| `block_number`              | Block B                    |
| `house_or_apartment_number` | H-04                       |
| `city`                      | Lahore                     |
| `province`                  | Punjab                     |
| `property_type`             | House or apartment         |
| `building_id`               | Apartment block identifier |

The model does not need the resident’s name, CNIC or employee number.

---

# 3. Physical property characteristics

These fields describe the structure of the house or apartment.

| Field                   | Description                      |
| ----------------------- | -------------------------------- |
| `construction_year`     | Year the property was built      |
| `property_age_years`    | Current age of the property      |
| `covered_area_sqft`     | Covered area                     |
| `plot_area_sqft`        | For houses                       |
| `number_of_floors`      | Total floors                     |
| `floor_number`          | For apartments                   |
| `number_of_bedrooms`    | Bedrooms                         |
| `number_of_bathrooms`   | Bathrooms                        |
| `number_of_kitchens`    | Kitchens                         |
| `number_of_occupants`   | Preferably grouped or anonymized |
| `construction_material` | Brick, concrete, mixed           |
| `roof_type`             | RCC slab, sheet, tile            |
| `flooring_type`         | Tile, marble, concrete           |
| `plumbing_type`         | GI, PVC, PPRC, mixed             |
| `electrical_wiring_age` | Years since installation         |
| `water_supply_type`     | Municipal, bore, mixed           |
| `sewerage_type`         | Central sewer, septic            |
| `water_tank_type`       | Concrete, plastic, steel         |

Important variables usually include:

* Property age
* Covered area
* Number of bathrooms
* Wiring age
* Plumbing age
* Roof type
* Number of occupants

---

# 4. Current condition data

A recent property inspection can provide some of the strongest prediction features.

Use a score such as:

```text
1 = Excellent
2 = Good
3 = Fair
4 = Poor
5 = Critical
```

Recommended condition fields:

| Field                         | Description                         |
| ----------------------------- | ----------------------------------- |
| `roof_condition_score`        | Roof condition                      |
| `wall_condition_score`        | Walls and plaster                   |
| `foundation_condition_score`  | Foundation and structural condition |
| `paint_condition_score`       | Internal and external paint         |
| `plumbing_condition_score`    | Pipes, taps and water supply        |
| `electrical_condition_score`  | Wiring, switches and boards         |
| `sewerage_condition_score`    | Drainage and sewerage               |
| `floor_condition_score`       | Floor and tiles                     |
| `door_window_condition_score` | Doors and windows                   |
| `bathroom_condition_score`    | Bathroom fixtures                   |
| `kitchen_condition_score`     | Kitchen fixtures                    |
| `water_tank_condition_score`  | Water tank                          |
| `overall_condition_score`     | Overall property condition          |

You can also add Yes/No fields:

* `roof_leakage_present`
* `wall_cracks_present`
* `dampness_present`
* `pipe_leakage_present`
* `exposed_wiring_present`
* `blocked_drainage_present`
* `termite_damage_present`
* `water_seepage_present`

---

# 5. Historical maintenance records

This is the most important data source.

Every historical maintenance activity should ideally have its own record.

| Field                  | Description                            |
| ---------------------- | -------------------------------------- |
| `work_order_id`        | Unique maintenance job                 |
| `property_id`          | Property where work occurred           |
| `complaint_date`       | Complaint date                         |
| `inspection_date`      | Inspection date                        |
| `repair_start_date`    | Work start                             |
| `completion_date`      | Work completion                        |
| `maintenance_category` | Plumbing, electrical, roofing, etc.    |
| `maintenance_type`     | Preventive, corrective or emergency    |
| `problem_description`  | Description of the issue               |
| `component_repaired`   | Pipe, roof, wall, switchboard          |
| `repair_or_replace`    | Repair or replacement                  |
| `priority`             | Low, normal, high, emergency           |
| `material_cost_pkr`    | Material cost                          |
| `labour_cost_pkr`      | Labour cost                            |
| `contractor_cost_pkr`  | Contractor cost                        |
| `transport_cost_pkr`   | Transport cost                         |
| `other_cost_pkr`       | Other cost                             |
| `total_cost_pkr`       | Total actual cost                      |
| `days_to_complete`     | Resolution time                        |
| `repeat_problem`       | Whether the same issue happened before |
| `contractor_id`        | Contractor identifier                  |
| `warranty_available`   | Whether covered by warranty            |

Maintenance categories should be standardized, such as:

* Plumbing
* Electrical
* Roofing
* Civil and structural
* Paint
* Flooring
* Doors and windows
* Sewerage and drainage
* Water supply
* Kitchen
* Bathroom
* HVAC
* Boundary wall
* Emergency repair

---

# 6. Aggregated maintenance history

From the detailed work-order records, create model features for each house or apartment.

Recommended fields:

| Field                                  | Description                 |
| -------------------------------------- | --------------------------- |
| `maintenance_cost_last_12_months_pkr`  | Total previous-year cost    |
| `maintenance_cost_last_24_months_pkr`  | Previous two-year cost      |
| `average_annual_cost_last_3_years_pkr` | Three-year average          |
| `number_of_repairs_last_12_months`     | Total repairs               |
| `number_of_emergency_repairs`          | Emergency jobs              |
| `number_of_plumbing_repairs`           | Plumbing jobs               |
| `number_of_electrical_repairs`         | Electrical jobs             |
| `number_of_repeat_failures`            | Repeated problems           |
| `days_since_last_repair`               | Time since last maintenance |
| `highest_single_repair_cost_pkr`       | Largest recent repair       |
| `average_repair_cost_pkr`              | Mean work-order cost        |
| `open_maintenance_requests`            | Unresolved complaints       |

These aggregated fields are normally more useful to the model than raw descriptions alone.

---

# 7. Renovation and component replacement history

A property’s age alone can be misleading. A 30-year-old property renovated recently may cost less than a 15-year-old property that has never been repaired.

| Field                            | Description              |
| -------------------------------- | ------------------------ |
| `last_major_renovation_date`     | Last major renovation    |
| `years_since_major_renovation`   | Years since renovation   |
| `last_roof_replacement_date`     | Roof replacement         |
| `last_plumbing_replacement_date` | Plumbing replacement     |
| `last_wiring_replacement_date`   | Wiring replacement       |
| `last_paint_date`                | Last complete paint      |
| `last_floor_replacement_date`    | Flooring replacement     |
| `renovation_cost_pkr`            | Previous renovation cost |
| `component_warranty_expiry`      | Warranty end date        |

---

# 8. Occupancy and usage information

Property usage affects deterioration.

| Field                               | Description                            |
| ----------------------------------- | -------------------------------------- |
| `occupancy_status`                  | Occupied, vacant or partially occupied |
| `number_of_occupants`               | Number of residents                    |
| `months_occupied_last_year`         | Occupied months                        |
| `vacancy_duration_months`           | Vacancy duration                       |
| `average_monthly_water_usage`       | Water usage                            |
| `average_monthly_electricity_usage` | Electricity usage                      |
| `unauthorized_modifications`        | Yes or No                              |
| `usage_intensity`                   | Low, medium or high                    |

For privacy, use property-level values rather than personal information about residents.

---

# 9. Complaint history

Complaints can indicate upcoming failures even before repair costs are incurred.

| Field                              | Description                 |
| ---------------------------------- | --------------------------- |
| `complaints_last_3_months`         | Recent complaints           |
| `complaints_last_12_months`        | Annual complaints           |
| `repeat_complaints_last_12_months` | Repeated issues             |
| `unresolved_complaints`            | Currently unresolved        |
| `average_resolution_days`          | Resolution time             |
| `emergency_complaints`             | Emergency complaints        |
| `plumbing_complaints`              | Plumbing-related complaints |
| `electrical_complaints`            | Electrical complaints       |
| `roof_leakage_complaints`          | Roof complaints             |

Complaint descriptions can later be analysed using NLP, but for the first POC, standardized categories are sufficient.

---

# 10. Location and environmental data

The same type of house may have different maintenance costs in different locations.

| Field                               | Description                 |
| ----------------------------------- | --------------------------- |
| `city`                              | City                        |
| `climate_zone`                      | Hot, humid, dry, cold       |
| `annual_rainfall_mm`                | Rainfall                    |
| `average_temperature_c`             | Temperature                 |
| `humidity_percentage`               | Humidity                    |
| `flood_risk_level`                  | Low, medium, high           |
| `waterlogging_incidents`            | Number of incidents         |
| `dust_exposure_level`               | Low, medium, high           |
| `water_quality_level`               | Good, moderate, poor        |
| `distance_to_supplier_km`           | Material transport distance |
| `distance_to_maintenance_office_km` | Service distance            |

Environmental data is particularly relevant for:

* Roof leakage
* Dampness
* Pipe corrosion
* Paint deterioration
* Drainage failures

---

# 11. Cost and economic data

The model should account for changes in prices over time.

| Field                       | Description                       |
| --------------------------- | --------------------------------- |
| `year`                      | Financial year                    |
| `material_price_index`      | Construction material price level |
| `labour_rate_index`         | Labour-rate change                |
| `cement_price_pkr`          | Average cement price              |
| `steel_price_pkr`           | Average steel price               |
| `paint_price_index`         | Paint-price change                |
| `plumbing_material_index`   | Pipe and fitting prices           |
| `electrical_material_index` | Electrical component prices       |
| `inflation_rate`            | Annual inflation                  |
| `contractor_rate_index`     | Contractor-rate change            |

Otherwise, the model may underestimate future costs when labour and material prices rise.

---

# 12. Apartment-specific data

For apartments, include additional variables because some costs are shared across the building.

| Field                                    | Description                 |
| ---------------------------------------- | --------------------------- |
| `apartment_floor_number`                 | Apartment floor             |
| `total_floors_in_building`               | Building height             |
| `total_apartments_in_block`              | Number of units             |
| `lift_available`                         | Yes or No                   |
| `lift_age_years`                         | Lift age                    |
| `shared_water_tank`                      | Yes or No                   |
| `shared_sewerage_system`                 | Yes or No                   |
| `shared_roof`                            | Yes                         |
| `common_area_condition_score`            | Shared area condition       |
| `building_exterior_condition_score`      | External condition          |
| `shared_maintenance_cost_allocation_pkr` | Apartment’s allocated share |

You must decide whether the prediction represents:

1. Maintenance cost inside the apartment only, or
2. Apartment-specific cost plus its share of common building maintenance.

That definition must remain consistent throughout the dataset.

---

# 13. Minimum dataset for the first POC

When data is limited, begin with these fields:

```text
property_id
property_type
colony_id
city
construction_year
property_age_years
covered_area_sqft
number_of_bedrooms
number_of_bathrooms
occupancy_status
number_of_occupants
years_since_major_renovation
roof_condition_score
plumbing_condition_score
electrical_condition_score
sewerage_condition_score
overall_condition_score
maintenance_cost_last_12_months_pkr
average_annual_cost_last_3_years_pkr
number_of_repairs_last_12_months
number_of_emergency_repairs
number_of_repeat_complaints
annual_rainfall_mm
material_price_index
maintenance_cost_next_12_months_pkr
```

This is a reasonable minimum feature set for a proof of concept.

---

# 14. Example training row

| Field                                  |     Example value |
| -------------------------------------- | ----------------: |
| `property_id`                          | WAPDA-LHR-B12-H04 |
| `property_type`                        |             House |
| `property_age_years`                   |                27 |
| `covered_area_sqft`                    |             2,100 |
| `number_of_bathrooms`                  |                 3 |
| `number_of_occupants`                  |                 6 |
| `years_since_major_renovation`         |                11 |
| `roof_condition_score`                 |                 4 |
| `plumbing_condition_score`             |                 5 |
| `electrical_condition_score`           |                 3 |
| `maintenance_cost_last_12_months_pkr`  |           185,000 |
| `average_annual_cost_last_3_years_pkr` |           162,000 |
| `number_of_repairs_last_12_months`     |                 7 |
| `number_of_repeat_complaints`          |                 3 |
| `material_price_index`                 |              1.14 |
| `maintenance_cost_next_12_months_pkr`  |           310,000 |

The final field is the historical value used as the model’s prediction target.

---

# 15. How much historical data is needed?

For a basic POC, aim for:

* At least **>500 properties** in the training corpus (WASC seed remains 101 framing units)
* At least **3 years of maintenance history**
* Preferably **5 years**
* At least **1,500–2,000 completed maintenance records**
* Data from more than one site/stratum analogous to colonies
* A mix of old and new properties
* A mix of low-cost and high-cost properties

Under current access limits, volume comes from a **harmonized public multi-source corpus**, not from WAPDA operational exports. See [DatasetPolicy.md](DatasetPolicy.md).

A useful structure could be:

```text
500 properties × 4 historical years
= 2,000 property-year training rows
```

More data is desirable, but data quality, lineage, and correct property identifiers are more important than simply having a large number of rows.

---

# 16. Data that should not be used

You generally do not need:

* Resident names
* CNIC numbers
* Personal phone numbers
* Salary information
* Employee designation, unless property allocation category directly affects property type
* Personal family details
* Information unrelated to property usage

Use anonymized property and colony IDs.

---

# 17. Most important data requirements

The five most important groups are:

1. **Actual historical maintenance costs**
2. **Property age, size and structural characteristics**
3. **Recent inspection and condition scores**
4. **Previous repairs, complaints and repeat failures**
5. **Renovation history and current material/labour price levels**

The project is feasible when each maintenance expense can be linked to:

```text
Property ID
+ maintenance date
+ maintenance category
+ actual cost
```

Without this linkage, the model cannot learn which characteristics caused a specific house or apartment to incur higher maintenance costs.
