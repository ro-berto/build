# How to update the protos

This directory holds the `stats.proto` produced by re-client, which is used to define the BigQuery schema. Since re-client itself is not open sourced yet, as a start, we will need to manually mirror the `stats.proto` from the re-client repo whenever we need to update the schema.

Here are the steps:

1. Copy over the proto from http://cs/foundry-x-re-client/api/stats/stats.proto
to `//recipe_proto/go.chromium.org/foundry-x/re-client/api/stats/stats.proto`.
1. Inside `//recipe_modules/reclient`, run:

```
bqschemaupdater -table $TABLE_NAME -message recipe_modules.build.reclient.RbeMetricsBq
```

| TODO(crbug.com/1152962): automate the proto mirroring process |
|---------------------------------------------------------------|