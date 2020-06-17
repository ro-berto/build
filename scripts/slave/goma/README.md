This directory contains goma-related protobuf to be uploaded with
`infra.libs.bigquery.helper.send_rows`.

Ideally, the files in this directory will be moved under the `recipes` or
`recipe_modules` directories in the `scripts/slave` directory as resources.

# Directory contents

The files are currently being used in the following locations:

* `\_\_init\_\_.py` - Needed for modules to import modules from this directory
* `compile\_events\_pb2.py` - Used by `scripts/slave/goma\_bq\_utils.py`
  * `counterz\_pb2.py`, `goma\_stats\_pb2.py` - Dependencies of
    `compile\_events\_pb2.py`
  * `compile\_events.proto` - Proto definition that `compile\_events\_pb2.py`,
    `counterz\_pb2.py` and `goma\_stats\_pb2.py` are generated from

## How to update `*_pb2.py` files?

1. Download [goma\_stats.proto](https://chromium.googlesource.com/infra/goma/client/+/master/lib/goma_stats.proto).
1. Install the latest [protobuf library](https://github.com/google/protobuf).
1. Execute following command to generate pb2.py files, and check them in.
```
 $ protoc --python_out=. compile_events.proto goma_stats.proto
