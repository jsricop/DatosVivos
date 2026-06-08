# Auditoría de calidad — catálogo Socrata vs `_audit_snapshot`

Generado: 2026-06-08T23:06:29.448202+00:00

- Snapshot local: 23854 datasets
- Datasets en Discovery (dominio entero): 18420
- En snapshot pero no en Discovery: 5441
- En Discovery pero no en snapshot: 6
- Datasets nativos procesados: 8420
- Datasets federated_href procesados: 9994

## Nativos

### Match por columna — nativos

| columna | comparados | match | mismatch | %match |
|---|---:|---:|---:|---:|
| name | 8420 | 8420 | 0 | 100.0% |
| entity_raw | 8420 | 8420 | 0 | 100.0% |
| category | 8420 | 8420 | 0 | 100.0% |
| description | 8420 | 8420 | 0 | 100.0% |
| data_updated_at | 8420 | 8341 | 79 | 99.1% |
| metadata_updated_at | 8420 | 8408 | 12 | 99.9% |
| publication_date | 8420 | 8420 | 0 | 100.0% |
| created_at_socrata | 8420 | 8420 | 0 | 100.0% |
| update_frequency | 8420 | 8420 | 0 | 100.0% |
| cobertura_geografica | 8420 | 8420 | 0 | 100.0% |
| sector | 8420 | 8420 | 0 | 100.0% |
| provenance | 8420 | 8420 | 0 | 100.0% |
| license | 8420 | 8420 | 0 | 100.0% |
| download_count | 8420 | 8407 | 13 | 99.8% |
| page_views_total | 8420 | 8403 | 17 | 99.8% |
| view_count | 8420 | 8403 | 17 | 99.8% |
| page_views_last_week | 8420 | 3231 | 5189 | 38.4% |
| page_views_last_month | 8420 | 7710 | 710 | 91.6% |

#### data_updated_at — ejemplos de mismatch (máx 10)
- `p6dx-8zbt` · local=`2026-06-07 15:30:22+00:00` · socrata=`2026-06-08T22:56:30.000Z`
- `jbjy-vk9h` · local=`2026-06-07 13:51:02+00:00` · socrata=`2026-06-08T20:06:01.000Z`
- `rpmr-utcd` · local=`2026-06-07 16:29:36+00:00` · socrata=`2026-06-08T14:43:52.000Z`
- `f789-7hwg` · local=`2026-06-07 19:28:43+00:00` · socrata=`2026-06-08T16:54:23.000Z`
- `hp9r-jxuu` · local=`2026-06-07 09:00:16+00:00` · socrata=`2026-06-08T09:00:35.000Z`
- `qhpu-8ixx` · local=`2026-06-05 15:27:51+00:00` · socrata=`2026-06-08T14:59:08.000Z`
- `62tk-nxj5` · local=`2026-06-07 06:16:33+00:00` · socrata=`2026-06-08T06:16:38.000Z`
- `iaeu-rcn6` · local=`2026-06-07 07:11:14+00:00` · socrata=`2026-06-08T07:14:06.000Z`
- `sr9n-792w` · local=`2026-06-05 13:00:02+00:00` · socrata=`2026-06-08T13:00:02.000Z`
- `rgxm-mmea` · local=`2026-06-07 06:31:57+00:00` · socrata=`2026-06-08T06:35:29.000Z`

#### metadata_updated_at — ejemplos de mismatch (máx 10)
- `qhpu-8ixx` · local=`2026-06-05 14:49:44+00:00` · socrata=`2026-06-08T14:50:50.000Z`
- `axk9-g2nh` · local=`2026-06-05 14:06:26+00:00` · socrata=`2026-06-08T14:05:45.000Z`
- `gpzw-wmxd` · local=`2026-06-05 13:23:23+00:00` · socrata=`2026-06-08T13:42:40.000Z`
- `uawh-cjvi` · local=`2026-06-05 13:00:42+00:00` · socrata=`2026-06-08T13:00:38.000Z`
- `hds9-4524` · local=`2026-06-05 13:07:04+00:00` · socrata=`2026-06-08T13:06:33.000Z`
- `eenq-ga7s` · local=`2026-06-07 05:22:04+00:00` · socrata=`2026-06-08T05:21:14.000Z`
- `te39-v28f` · local=`2026-06-07 05:22:23+00:00` · socrata=`2026-06-08T05:21:03.000Z`
- `sfpk-jthu` · local=`2026-06-07 05:27:19+00:00` · socrata=`2026-06-08T05:26:34.000Z`
- `p68r-quzd` · local=`2026-06-07 05:22:16+00:00` · socrata=`2026-06-08T05:21:09.000Z`
- `v84h-4xks` · local=`2026-06-07 05:22:09+00:00` · socrata=`2026-06-08T05:21:04.000Z`

#### download_count — ejemplos de mismatch (máx 10)
- `85nn-ccay` · local=`36` · socrata=`38`
- `mn2x-eebm` · local=`38` · socrata=`40`
- `6cdm-nmjd` · local=`40` · socrata=`43`
- `8dy7-78in` · local=`37` · socrata=`39`
- `4hi2-qp6e` · local=`20` · socrata=`22`
- `ng6i-i4ac` · local=`27` · socrata=`29`
- `m5gk-zghe` · local=`17` · socrata=`19`
- `82r3-xv8q` · local=`17` · socrata=`18`
- `ycr9-fq4u` · local=`36` · socrata=`38`
- `qnm3-mrmp` · local=`21` · socrata=`23`

#### page_views_total — ejemplos de mismatch (máx 10)
- `9n3n-m2kt` · local=`194` · socrata=`211`
- `ra9d-rjtg` · local=`190` · socrata=`204`
- `h2di-r38w` · local=`158` · socrata=`167`
- `xz3e-gd9c` · local=`145` · socrata=`161`
- `psni-qaps` · local=`145` · socrata=`156`
- `yrjq-67s8` · local=`142` · socrata=`150`
- `cktq-4ubk` · local=`136` · socrata=`147`
- `2swj-9ez8` · local=`133` · socrata=`140`
- `vxwa-tusk` · local=`127` · socrata=`137`
- `ah8d-b5jz` · local=`126` · socrata=`135`

#### view_count — ejemplos de mismatch (máx 10)
- `9n3n-m2kt` · local=`194` · socrata=`211`
- `ra9d-rjtg` · local=`190` · socrata=`204`
- `h2di-r38w` · local=`158` · socrata=`167`
- `xz3e-gd9c` · local=`145` · socrata=`161`
- `psni-qaps` · local=`145` · socrata=`156`
- `yrjq-67s8` · local=`142` · socrata=`150`
- `cktq-4ubk` · local=`136` · socrata=`147`
- `2swj-9ez8` · local=`133` · socrata=`140`
- `vxwa-tusk` · local=`127` · socrata=`137`
- `ah8d-b5jz` · local=`126` · socrata=`135`

#### page_views_last_week — ejemplos de mismatch (máx 10)
- `p6dx-8zbt` · local=`6036` · socrata=`5392`
- `jbjy-vk9h` · local=`14792` · socrata=`13173`
- `i7cb-raxc` · local=`6642` · socrata=`6262`
- `rpmr-utcd` · local=`6158` · socrata=`5795`
- `ae7u-y7m2` · local=`372` · socrata=`342`
- `32sa-8pi3` · local=`1978` · socrata=`1788`
- `i3kx-3zps` · local=`32911` · socrata=`30925`
- `ji8i-4anb` · local=`399` · socrata=`379`
- `2waz-acaa` · local=`678` · socrata=`571`
- `ii2p-naes` · local=`236` · socrata=`222`

#### page_views_last_month — ejemplos de mismatch (máx 10)
- `sgp4-3e6k` · local=`424` · socrata=`398`
- `es62-3x6p` · local=`316` · socrata=`300`
- `u8du-s7mh` · local=`204` · socrata=`215`
- `xbc7-65j4` · local=`292` · socrata=`274`
- `x62z-xik8` · local=`191` · socrata=`179`
- `8rpn-wpty` · local=`2735` · socrata=`2884`
- `vy9n-w6hc` · local=`171` · socrata=`162`
- `van8-pi8b` · local=`167` · socrata=`156`
- `4ypt-m8ys` · local=`149` · socrata=`138`
- `65mn-ybz5` · local=`231` · socrata=`217`

## Federados (`federated_href`)

### Match por columna — federados

| columna | comparados | match | mismatch | %match |
|---|---:|---:|---:|---:|
| name | 9994 | 9994 | 0 | 100.0% |
| entity_raw | 9994 | 9994 | 0 | 100.0% |
| category | 9994 | 9994 | 0 | 100.0% |
| description | 9994 | 9994 | 0 | 100.0% |
| data_updated_at | 9994 | 9994 | 0 | 100.0% |
| metadata_updated_at | 9994 | 9882 | 112 | 98.9% |
| publication_date | 9994 | 9994 | 0 | 100.0% |
| created_at_socrata | 9994 | 9994 | 0 | 100.0% |
| update_frequency | 9994 | 9994 | 0 | 100.0% |
| cobertura_geografica | 9994 | 1022 | 8972 | 10.2% |
| sector | 9994 | 9994 | 0 | 100.0% |
| provenance | 9994 | 9994 | 0 | 100.0% |
| license | 9994 | 9994 | 0 | 100.0% |
| download_count | 9994 | 9994 | 0 | 100.0% |
| page_views_total | 9994 | 9743 | 251 | 97.5% |
| view_count | 9994 | 9743 | 251 | 97.5% |
| page_views_last_week | 9994 | 4441 | 5553 | 44.4% |
| page_views_last_month | 9994 | 8805 | 1189 | 88.1% |

#### metadata_updated_at — ejemplos de mismatch (máx 10)
- `hfii-knfn` · local=`2026-06-07 19:09:36+00:00` · socrata=`2026-06-08T19:05:01.000Z`
- `4jum-zayu` · local=`2026-06-07 19:12:00+00:00` · socrata=`2026-06-08T19:13:02.000Z`
- `632p-wvm7` · local=`2026-06-07 19:15:03+00:00` · socrata=`2026-06-08T19:15:56.000Z`
- `6g2y-iw65` · local=`2026-06-07 19:14:56+00:00` · socrata=`2026-06-08T19:15:52.000Z`
- `d6ck-xfhn` · local=`2026-06-07 19:01:44+00:00` · socrata=`2026-06-08T19:01:54.000Z`
- `ajby-ju3v` · local=`2026-06-07 19:09:35+00:00` · socrata=`2026-06-08T19:05:00.000Z`
- `8k9i-ev4h` · local=`2026-06-07 19:04:36+00:00` · socrata=`2026-06-08T19:04:51.000Z`
- `wfw5-p98n` · local=`2026-06-07 19:09:35+00:00` · socrata=`2026-06-08T19:05:00.000Z`
- `x85u-zv33` · local=`2026-06-06 19:04:15+00:00` · socrata=`2026-06-08T19:04:43.000Z`
- `p596-kjww` · local=`2026-06-07 19:14:58+00:00` · socrata=`2026-06-08T19:15:53.000Z`

#### cobertura_geografica — ejemplos de mismatch (máx 10)
- `4dai-7crq` · local=`Nacional` · socrata=`None`
- `se7p-ytdd` · local=`Municipal` · socrata=`None`
- `f6du-dwd8` · local=`Nacional` · socrata=`None`
- `nht7-gfb8` · local=`Nacional` · socrata=`None`
- `3itm-5dx4` · local=`Nacional` · socrata=`None`
- `2kyx-shwz` · local=`Nacional` · socrata=`None`
- `2ie9-7xta` · local=`Nacional` · socrata=`None`
- `wrs4-irpf` · local=`Municipal` · socrata=`None`
- `nzw7-qjkr` · local=`Departamental` · socrata=`None`
- `w66c-tjsq` · local=`Nacional` · socrata=`None`

#### page_views_total — ejemplos de mismatch (máx 10)
- `bruu-7i5m` · local=`238` · socrata=`251`
- `t5vm-x57r` · local=`210` · socrata=`223`
- `tfti-9uws` · local=`190` · socrata=`200`
- `jrwx-udes` · local=`189` · socrata=`199`
- `rv9q-4ff6` · local=`180` · socrata=`193`
- `fb79-g5e2` · local=`178` · socrata=`191`
- `de6i-46hh` · local=`176` · socrata=`186`
- `trgu-yxt6` · local=`172` · socrata=`185`
- `i7v9-pugr` · local=`174` · socrata=`184`
- `gx6q-seu5` · local=`171` · socrata=`180`

#### view_count — ejemplos de mismatch (máx 10)
- `bruu-7i5m` · local=`238` · socrata=`251`
- `t5vm-x57r` · local=`210` · socrata=`223`
- `tfti-9uws` · local=`190` · socrata=`200`
- `jrwx-udes` · local=`189` · socrata=`199`
- `rv9q-4ff6` · local=`180` · socrata=`193`
- `fb79-g5e2` · local=`178` · socrata=`191`
- `de6i-46hh` · local=`176` · socrata=`186`
- `trgu-yxt6` · local=`172` · socrata=`185`
- `i7v9-pugr` · local=`174` · socrata=`184`
- `gx6q-seu5` · local=`171` · socrata=`180`

#### page_views_last_week — ejemplos de mismatch (máx 10)
- `f6du-dwd8` · local=`122` · socrata=`113`
- `nht7-gfb8` · local=`62` · socrata=`58`
- `nzw7-qjkr` · local=`83` · socrata=`71`
- `w66c-tjsq` · local=`38` · socrata=`36`
- `gnu2-nwsw` · local=`64` · socrata=`59`
- `ix2x-srre` · local=`72` · socrata=`65`
- `dx2g-2mhm` · local=`118` · socrata=`108`
- `vg4f-q9p9` · local=`152` · socrata=`135`
- `ke8u-qixu` · local=`60` · socrata=`51`
- `k8xg-2q2b` · local=`35` · socrata=`30`

#### page_views_last_month — ejemplos de mismatch (máx 10)
- `3fqj-86mk` · local=`215` · socrata=`196`
- `87gf-2mb9` · local=`128` · socrata=`135`
- `7z2b-5cer` · local=`88` · socrata=`83`
- `rr8q-xvjs` · local=`129` · socrata=`120`
- `tjwg-66d7` · local=`219` · socrata=`234`
- `gh47-3cyc` · local=`243` · socrata=`228`
- `9uyb-9tt4` · local=`125` · socrata=`116`
- `ujwb-uu78` · local=`117` · socrata=`130`
- `8wbk-ytxv` · local=`88` · socrata=`95`
- `8q6m-ga98` · local=`188` · socrata=`169`
