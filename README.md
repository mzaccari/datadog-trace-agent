### Make it work

#### The Agent

1. Enable your personal-chef [godev environment](https://github.com/DataDog/devops/wiki/Development-Environment#select-your-environment)

2. Download [ES 2.0+](https://www.elastic.co/downloads/elasticsearch), extract, and run: 
  ```
  $ wget https://download.elastic.co/elasticsearch/release/org/elasticsearch/distribution/tar/elasticsearch/2.3.1/elasticsearch-2.3.1.tar.gz
  $ tar xvfz elasticsearch-2.3.1.tar.gz
  $ ./elasticsearch-2.3.1/bin/elasticsearch
  # If there is a JVM conflict, and Elasticsearch refuses to start, run the below workaround
  $ JAVA_OPTS='-XX:-UseSuperWord' ./elasticsearch-2.3.1/bin/elasticsearch -d
  ```
3. Setup ES schema

  ```
  rake trace:reset_es
  ```
4. Setup Cassandra chema

  ```
  $ goforit
  $ rake db:cass_rebuild
  (If the above errors, probably a cqlsh issue, just use the defaults)
  $ cqlsh -f ./etc/dbs/trace.cql
  ```

5. Ensure latest trace apps are installed: the webapp speaks to smelter and Elasticsearch directly for the Trace UI,
and submits it's own traces via the trace-agent receiver (by default listening on localhost:7777 in your VM)
  ```
  $ goforit
  $ rake trace:install
  ```

6. Run It
  ```
  $ supe start trace:
  ```


#### Checking it works
Ensure that consul flags for tracing are enabled in the webapp (they should be on by default)
```
$ consulkv get config/datadog/dev/features/trace_pylons
{

  "default": true,

  "disabled_orgs": [],

  "enabled_orgs": [],

  "help": "Tracing of Pylons",

  "pct_of_orgs": null

}

$ consulkv get config/datadog/dev/features/trace_psycopg2
{

  "default": true,

  "disabled_orgs": [],

  "enabled_orgs": [],

  "help": "Tracing of psycopg2",

  "pct_of_orgs": null

}
```
We actually only query for this flag once, at app startup - so if you change its value you will have to restart mcnulty
```
$ supe restart core:mcnulty
```

To verify the webapp is sending spans, watch out for lines like this in `/var/log/dogweb/mcnulty.log`
```
2016-04-14 12:06:52 INFO dogtrace.reporter (reporter.py:40) - Reporting 9 spans
```

Once satisfied that the webapp is reporting, you can check that your spans are handled as you expect downstream.
Look out for lines like this in `/var/log/dd-go/trace-agent.log`
```
2016-04-14 12:13:16 INFO (resource_quantile.go:109) - Sampled 1 traces out of 1, 9 spans out of 9, in 50.287µs
2016-04-14 12:13:16 DEBUG (sampler.go:55) - Sampler flushes 9 spans
```

and further down the pipe in `/var/log/dd-go/trace_api.log`
```
127.0.0.1 - - [14/Apr/2016:12:22:31 +0000] "POST /api/v0.1/collector?api_key=apikey_2 HTTP/1.1" 202 0
2016-04-14 12:22:32 INFO (server.go:184) - processed plds(ok:1438 rej:0) spans(total:2278 per_pld:1.58 rej_rate:0.00%), pps: 0.20/s (0.19/s), sps: 4.81/s (0.30/s), rpps: 0.00/s (0.00/s)
```

If you are not seeing what you expect in the above steps, see Troubleshooting

#### The Python lib

Checkout `dogweb:dogtrace` to have access to the `dogtrace` library.


#### Troubleshooting / Gotchas
##### My traces are being dropped

Trace API will reject spans that it cannot resolve a host for (currently it does not create hosts)
If this is happening you will see a bunch of lines like this in `/var/log/dd-go/trace_api.log`

```
2016-04-14 10:56:01 ERROR (resolver.go:64) - Dropping span Span[tid:8914676175975151832,sid:208494955,app:dogweb,ser:pylons,nam:pylons.middleware.routes,res:__call__], reason: ResolvedSpan.Normalize: host ID must be set in span
```

1. Check that a host exists in PG whose name matches the value of the `hostname` syscall (raclette gets this via `os.Hostname()` in go)
  ```
  $ cd ~/workspace/dogweb
  $ rake cli:psql
  dogdata=# select * from host;
  ```

  If such a host doesn't exist, it's probably because dd-agent is submitting a hostname that doesn't match
  the one raclette submits. To resolve:

2. Ensure core services are running
  ```
  $ supe status core:
  (If needed) $ supe start core:
  ```

3. Restore dd-agent to submitting the default hostname
  ```
  $ sudo sed -i.bak '/hostname/d' /etc/dd-agent/datadog.conf && sudo /etc/init.d/datadog-agent restart
  ```

4. Ensure the right host has made it to PG (Repeat Step 1 above)

5. Clear the Trace API's cache
  Check where trace api's redis instance lives
  ```
  $ goforit
  $ cat trace/apps/trace-api/etc/api.ini | grep cache_url
  cache_url = redis://localhost:6380/1
  ```
  Flush the above redis instance
  ```
  $ redis-cli -p 6380 -n 1 flushdb
  ```

You should now see spans coming in at `localhost:8090/trace/search`. If you don't, ping us in #raclette

##### Index Page showing blank
Index page relies on smelter statistics and smelter relies on the postgres table `smelter_aggregate` to know how to create aggregate stats.
If you see an empty trace index page, chances are the `smelter_aggregate` table in PG is empty. You can fix this with:

```
$ cd ~/workspace/dogweb
$ rake data:reload:trace`
```
