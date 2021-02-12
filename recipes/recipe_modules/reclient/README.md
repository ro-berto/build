# How to update the RBE metrics BigQuery schema

The process is based on Goma's [bqschema cheat sheet](https://g3doc.corp.google.com/devtools/goma/g3doc/developers/bqschema-cheat-sheet.md).

## One-time setup

If you have not created the BigQuery table, follow these steps:

1. Visit https://pantheon.corp.google.com/home/dashboard?project=goma-logs
1. Choose `BigQuery` in the big data menu
1. Select `goma-logs`, then `CREATE DATASET`
1. Create dataset and table. Make sure to choose `Empty Table`, as we will specify the schema later.


## Update the BigQuery table schema

1. Ensure that `bqschemaupdater` is in your path:

```sh
eval $(infra/go/env.py)
```

2. Inside `//recipe_modules/reclient`, run:

```sh
# Replace this if you are updating a different table
TABLE_NAME=goma-logs.rbe_metrics.builds

# -I is needed to find stats.proto
bqschemaupdater -table $TABLE_NAME -message recipe_modules.build.reclient.RbeMetricsBq -I ../../recipe_proto
```

## (Optional) Update the stats proto mirrored from re-client

It is good to keep `stats.proto` up-to-date, although you do not need to do this frequently. The procedure is documented in https://chromium.googlesource.com/chromium/tools/build/+/refs/heads/master/recipes/recipe_proto/go.chromium.org/foundry-x/re-client.