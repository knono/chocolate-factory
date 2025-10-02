---
description: "Admin InfluxDB - Chocolate Factory"
---

Admin de InfluxDB. Ejecuta comandos según: {{ARGUMENTS}}

Container: chocolate_factory_storage | Buckets: energy_data, siar_historical

```
# Health
docker exec chocolate_factory_storage influx ping
docker exec chocolate_factory_storage influx bucket list

# Last data
docker exec chocolate_factory_storage influx query 'from(bucket:"energy_data")|>range(start:-1h)|>filter(fn:(r)=>r._measurement=="energy_prices")|>last()'

# Gaps
docker exec chocolate_factory_storage influx query 'from(bucket:"energy_data")|>range(start:-7d)|>filter(fn:(r)=>r._measurement=="energy_prices")|>aggregateWindow(every:1h,fn:count)|>filter(fn:(r)=>r._value==0)'
```

Ejecuta comandos ahora.
