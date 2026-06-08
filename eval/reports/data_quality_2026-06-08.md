# Auditoría de calidad — catálogo Socrata vs `_audit_snapshot`

Generado: 2026-06-08T20:30:13.887460+00:00

- Snapshot local: 18402 datasets
- Datasets en Discovery (dominio entero): 18420
- En snapshot pero no en Discovery: 186
- En Discovery pero no en snapshot: 204
- Datasets nativos procesados: 8403
- Datasets federated_href procesados: 9813

## Nativos

### Match por columna — nativos

| columna | comparados | match | mismatch | %match |
|---|---:|---:|---:|---:|
| name | 8403 | 8400 | 3 | 100.0% |
| entity_raw | 8403 | 8399 | 4 | 100.0% |
| category | 8403 | 8403 | 0 | 100.0% |
| description | 8403 | 8376 | 27 | 99.7% |
| data_updated_at | 8403 | 8195 | 208 | 97.5% |
| metadata_updated_at | 8403 | 8289 | 114 | 98.6% |
| publication_date | 8403 | 8393 | 10 | 99.9% |
| created_at_socrata | 8403 | 8403 | 0 | 100.0% |
| update_frequency | 8403 | 8402 | 1 | 100.0% |
| cobertura_geografica | 8403 | 8401 | 2 | 100.0% |
| sector | 8403 | 8402 | 1 | 100.0% |
| provenance | 8403 | 8403 | 0 | 100.0% |
| license | 8403 | 8403 | 0 | 100.0% |
| download_count | 8403 | 6148 | 2255 | 73.2% |
| page_views_total | 8403 | 4439 | 3964 | 52.8% |
| view_count | 8403 | 4439 | 3964 | 52.8% |
| page_views_last_week | 8403 | 955 | 7448 | 11.4% |
| page_views_last_month | 8403 | 2615 | 5788 | 31.1% |

#### name — ejemplos de mismatch (máx 10)
- `gwqv-sqvs` · local=`BASE DE DATOS DE EMPRESAS Y/O ENTIDADES ACTIVAS - JURISDICCIÓN CÁMARA DE COMERCIO DE IBAGUÉ - CORTE A 30 DE ABRIL DE 202` · socrata=`BASE DE DATOS DE EMPRESAS Y/O ENTIDADES ACTIVAS - JURISDICCIÓN CÁMARA DE COMERCIO DE IBAGUÉ - CORTE A 31 DE MAYO DE 2026`
- `8hqm-7fdt` · local=`Desaparecidos en Colombia - Histórico marzo de 2026` · socrata=`Desaparecidos en Colombia - Histórico abril de 2026`
- `nbae-kzan` · local=`SECOP II - Archivos Descarga Historico` · socrata=`SECOP II - Archivos Descarga Historico 2024`

#### entity_raw — ejemplos de mismatch (máx 10)
- `tq4m-hmg2` · local=`Alcaldía de Belén de Umbría, Risaralda` · socrata=`Administradora de los Recursos del Sistema General de Seguridad Social en Salud`
- `d7a5-cnra` · local=`Alcaldía de La Virginia, Risaralda` · socrata=`Administradora de los Recursos del Sistema General de Seguridad Social en Salud`
- `7y7n-8wu6` · local=`Alcaldía de Sogamoso, Boyacá` · socrata=`Municipio de Sogamoso Boyacá`
- `xrhp-s6kz` · local=`Alcaldía de Magüí, Nariño` · socrata=`Alcaldía de Madrid Cundinamarca`

#### description — ejemplos de mismatch (máx 10)
- `h2yr-zfb2` · local=`El archivo contiene el número de hogares que en algún momento fueron beneficiarios del subsidio familiar de vivienda por` · socrata=`El archivo contiene el número de hogares que en algún momento fueron beneficiarios del subsidio familiar de vivienda por`
- `k8pa-bybh` · local=`Se muestra las veredas del municipio de Yopal y el corregimiento al que pertenece` · socrata=`Se muestra las veredas del municipio de Yopal y el corregimiento al que pertenece

La Administración Municipal de Yopal `
- `8hqm-7fdt` · local=`Corresponde a los datos históricos en el Sistema de Información Red de Desaparecidos y Cadáveres - SIRDEC de personas re` · socrata=`Corresponde a los datos históricos en el Sistema de Información Red de Desaparecidos y Cadáveres - SIRDEC de personas re`
- `tcwu-r53g` · local=`Contiene la información relacionada con el indicador: Personas con acceso a agua potable y saneamiento básico por primer` · socrata=`Contiene la información relacionada con el indicador: Personas con acceso a agua potable y saneamiento básico por primer`
- `wi7w-2nvm` · local=`Registro de las Ofertas cargadas en el sistema, por cada proceso de compra publica, desde el 01 de enero 2023` · socrata=`Registro de las Ofertas cargadas en el sistema, por cada proceso de compra publica, desde el 01 de enero 2024`
- `4xft-ng7z` · local=`El documento contiene los Proyectos viabilizados por el MVCT, registrados en el sistema de información SIGEVAS y su resp` · socrata=`El documento contiene los Proyectos viabilizados por el MVCT, registrados en el sistema de información SIGEVAS y su resp`
- `49da-69ff` · local=`El archivo contiene información por departamento y ciudad, correspondiente al número de viviendas por año, que se han co` · socrata=`El archivo contiene información por departamento y ciudad, correspondiente al número de viviendas por año, que se han co`
- `22ip-4jk2` · local=`La Secretaría de Movilidad de la Alcaldía del municipio de Fusagasugá da a conocer la base de datos de los Accidentes de` · socrata=`La Secretaría de Movilidad de la Alcaldía del municipio de Fusagasugá da a conocer la base de datos de los Accidentes de`
- `bnmy-mpts` · local=`Conjunto de Datos Maestro - Contiene el número de hogares que en algún momento fueron beneficiarios del subsidio familia` · socrata=`Conjunto de Datos Maestro - Contiene el número de hogares que en algún momento fueron beneficiarios del subsidio familia`
- `g85v-p2ik` · local=`Información histórica de beneficiarios colombianos en el exterior de convocatorias a partir del año 2018 hasta el año 20` · socrata=`Información histórica de beneficiarios colombianos en el exterior de convocatorias a partir del año 2018 hasta el año 20`

#### data_updated_at — ejemplos de mismatch (máx 10)
- `p6dx-8zbt` · local=`2026-05-28 15:44:00+00:00` · socrata=`2026-06-07T15:30:22.000Z`
- `jbjy-vk9h` · local=`2026-05-28 16:38:43+00:00` · socrata=`2026-06-08T20:06:01.000Z`
- `i7cb-raxc` · local=`2026-05-22 16:26:30+00:00` · socrata=`2026-05-29T18:30:04.000Z`
- `rpmr-utcd` · local=`2026-05-28 14:21:25+00:00` · socrata=`2026-06-08T14:43:52.000Z`
- `vwwf-4ftk` · local=`2026-05-22 17:00:24+00:00` · socrata=`2026-05-29T18:13:41.000Z`
- `vgr4-gemg` · local=`2026-05-22 17:13:47+00:00` · socrata=`2026-05-29T18:38:22.000Z`
- `spzp-dfuc` · local=`2026-05-22 17:33:45+00:00` · socrata=`2026-05-29T18:22:05.000Z`
- `32sa-8pi3` · local=`2026-05-28 23:05:31+00:00` · socrata=`2026-06-05T23:20:28.000Z`
- `f789-7hwg` · local=`2026-05-28 20:45:51+00:00` · socrata=`2026-06-08T16:54:23.000Z`
- `4zwu-ra3f` · local=`2026-05-23 04:43:27+00:00` · socrata=`2026-06-06T04:45:05.000Z`

#### metadata_updated_at — ejemplos de mismatch (máx 10)
- `i7cb-raxc` · local=`2026-05-22 16:23:12+00:00` · socrata=`2026-05-29T18:26:59.000Z`
- `vwwf-4ftk` · local=`2026-05-22 16:57:57+00:00` · socrata=`2026-05-29T18:10:05.000Z`
- `vgr4-gemg` · local=`2026-05-22 17:13:43+00:00` · socrata=`2026-05-29T18:38:19.000Z`
- `spzp-dfuc` · local=`2026-05-22 17:31:33+00:00` · socrata=`2026-05-29T18:19:18.000Z`
- `32sa-8pi3` · local=`2026-05-28 23:05:28+00:00` · socrata=`2026-06-05T23:20:26.000Z`
- `4zwu-ra3f` · local=`2026-05-23 04:43:25+00:00` · socrata=`2026-06-06T04:45:04.000Z`
- `h2yr-zfb2` · local=`2026-05-18 16:58:03+00:00` · socrata=`2026-06-04T14:59:47.000Z`
- `4w3i-wxax` · local=`2026-05-18 17:17:47+00:00` · socrata=`2026-06-02T15:15:03.000Z`
- `ii2p-naes` · local=`2026-05-25 21:04:01+00:00` · socrata=`2026-06-05T14:08:45.000Z`
- `sdmr-tfmf` · local=`2026-05-18 17:31:50+00:00` · socrata=`2026-06-05T17:30:13.000Z`

#### publication_date — ejemplos de mismatch (máx 10)
- `ii2p-naes` · local=`2026-05-25 21:04:01+00:00` · socrata=`2026-06-05T14:08:45.000Z`
- `qktb-5f8m` · local=`2026-05-20 21:21:37+00:00` · socrata=`2026-06-05T16:43:53.000Z`
- `wbu2-8yju` · local=`2026-05-28 18:19:46+00:00` · socrata=`2026-06-02T00:21:06.000Z`
- `3wwx-cbke` · local=`2023-05-08 21:01:29+00:00` · socrata=`2026-06-01T18:11:27.000Z`
- `psyr-i7bp` · local=`2026-05-20 21:29:30+00:00` · socrata=`2026-06-05T16:27:05.000Z`
- `9wsr-upab` · local=`2025-06-09 22:03:25+00:00` · socrata=`2026-06-01T13:49:51.000Z`
- `n3sv-26ws` · local=`2025-11-18 15:42:43+00:00` · socrata=`2026-06-01T14:02:50.000Z`
- `tuud-36vj` · local=`2024-10-04 21:14:32+00:00` · socrata=`2026-06-03T19:47:15.000Z`
- `ptea-49jy` · local=`2025-09-09 17:05:54+00:00` · socrata=`2026-06-01T14:26:10.000Z`
- `nbae-kzan` · local=`2026-05-02 07:53:15+00:00` · socrata=`2026-06-05T07:35:31.000Z`

#### update_frequency — ejemplos de mismatch (máx 10)
- `kfcm-k5vw` · local=`Semestral` · socrata=`Cuatrimestral`

#### cobertura_geografica — ejemplos de mismatch (máx 10)
- `tq4m-hmg2` · local=`Departamental` · socrata=`Nacional`
- `d7a5-cnra` · local=`Municipal` · socrata=`Nacional`

#### sector — ejemplos de mismatch (máx 10)
- `7y7n-8wu6` · local=`Planeación` · socrata=`Educación`

#### download_count — ejemplos de mismatch (máx 10)
- `sr9n-792w` · local=`10457` · socrata=`11318`
- `irrs-j2nx` · local=`3657` · socrata=`3942`
- `v2k4-2t8s` · local=`1686` · socrata=`1798`
- `jtqe-tuvf` · local=`3069` · socrata=`3256`
- `s5f2-yivs` · local=`1981` · socrata=`2089`
- `g5bx-sj75` · local=`203` · socrata=`214`
- `sji7-3uxf` · local=`1443` · socrata=`1572`
- `m66z-hn6g` · local=`13112` · socrata=`13826`
- `2iqs-g9cv` · local=`5158` · socrata=`5625`
- `seua-4ze8` · local=`430` · socrata=`469`

#### page_views_total — ejemplos de mismatch (máx 10)
- `i3kx-3zps` · local=`208637` · socrata=`262241`
- `4w3i-wxax` · local=`163854` · socrata=`180716`
- `m8fd-ahd9` · local=`26130` · socrata=`27536`
- `sgf4-8tf8` · local=`23988` · socrata=`26499`
- `s5f2-yivs` · local=`21029` · socrata=`23197`
- `tbmm-8d5r` · local=`20723` · socrata=`22134`
- `6jmc-vaxk` · local=`11187` · socrata=`11777`
- `8rpn-wpty` · local=`6749` · socrata=`8581`
- `5kjg-nuda` · local=`7698` · socrata=`8402`
- `d7zw-hpf4` · local=`6921` · socrata=`7662`

#### view_count — ejemplos de mismatch (máx 10)
- `i3kx-3zps` · local=`208637` · socrata=`262241`
- `4w3i-wxax` · local=`163854` · socrata=`180716`
- `m8fd-ahd9` · local=`26130` · socrata=`27536`
- `sgf4-8tf8` · local=`23988` · socrata=`26499`
- `s5f2-yivs` · local=`21029` · socrata=`23197`
- `tbmm-8d5r` · local=`20723` · socrata=`22134`
- `6jmc-vaxk` · local=`11187` · socrata=`11777`
- `8rpn-wpty` · local=`6749` · socrata=`8581`
- `5kjg-nuda` · local=`7698` · socrata=`8402`
- `d7zw-hpf4` · local=`6921` · socrata=`7662`

#### page_views_last_week — ejemplos de mismatch (máx 10)
- `gt2j-8ykr` · local=`769` · socrata=`642`
- `p6dx-8zbt` · local=`5995` · socrata=`5531`
- `jbjy-vk9h` · local=`16406` · socrata=`13594`
- `i7cb-raxc` · local=`5628` · socrata=`6347`
- `xfif-myr2` · local=`479` · socrata=`673`
- `rpmr-utcd` · local=`7084` · socrata=`5906`
- `vwwf-4ftk` · local=`560` · socrata=`523`
- `vgr4-gemg` · local=`293` · socrata=`202`
- `spzp-dfuc` · local=`254` · socrata=`202`
- `ae7u-y7m2` · local=`559` · socrata=`347`

#### page_views_last_month — ejemplos de mismatch (máx 10)
- `gt2j-8ykr` · local=`4001` · socrata=`3585`
- `i7cb-raxc` · local=`16872` · socrata=`19700`
- `vgr4-gemg` · local=`860` · socrata=`910`
- `spzp-dfuc` · local=`749` · socrata=`844`
- `ae7u-y7m2` · local=`1978` · socrata=`1861`
- `32sa-8pi3` · local=`9556` · socrata=`8389`
- `i3kx-3zps` · local=`91083` · socrata=`119645`
- `f789-7hwg` · local=`10130` · socrata=`11901`
- `4zwu-ra3f` · local=`1299` · socrata=`1715`
- `e97j-vuf7` · local=`1885` · socrata=`1656`

## Federados (`federated_href`)

### Match por columna — federados

| columna | comparados | match | mismatch | %match |
|---|---:|---:|---:|---:|
| name | 9813 | 9750 | 63 | 99.4% |
| entity_raw | 9813 | 9813 | 0 | 100.0% |
| category | 9813 | 9813 | 0 | 100.0% |
| description | 9813 | 9795 | 18 | 99.8% |
| data_updated_at | 9813 | 9813 | 0 | 100.0% |
| metadata_updated_at | 9813 | 9623 | 190 | 98.1% |
| publication_date | 9813 | 9813 | 0 | 100.0% |
| created_at_socrata | 9813 | 9813 | 0 | 100.0% |
| update_frequency | 9813 | 9813 | 0 | 100.0% |
| cobertura_geografica | 9813 | 9813 | 0 | 100.0% |
| sector | 9813 | 9813 | 0 | 100.0% |
| provenance | 9813 | 9813 | 0 | 100.0% |
| license | 9813 | 9813 | 0 | 100.0% |
| download_count | 9813 | 9813 | 0 | 100.0% |
| page_views_total | 9813 | 895 | 8918 | 9.1% |
| view_count | 9813 | 895 | 8918 | 9.1% |
| page_views_last_week | 9813 | 1511 | 8302 | 15.4% |
| page_views_last_month | 9813 | 1399 | 8414 | 14.3% |

#### name — ejemplos de mismatch (máx 10)
- `rfju-cn96` · local=`Base Catastral Publica del Gestor IGAC 04 2026` · socrata=`Base Catastral Pública del Gestor IGAC 04 2026`
- `wvbg-9pca` · local=`Base Catastral Publica del Gestor IGAC 04 2026` · socrata=`Base Catastral Pública del Gestor IGAC  Servicio WFS 04 2026`
- `uei5-r752` · local=`MDT. Municipio de Bituima. Centro poblado del Boquerón de Iló. GSD 1 m. 2023 (image)` · socrata=`MDT. Centro poblado del Boquerón de Iló. Municipio de Bituima del Departamento de Cundinamarca. GSD 1 m. 2023 (Image).`
- `ta6q-chrv` · local=`Ortofoto. Municipio de Cáqueza. GSD 10 cm. 2021 (Imagen)` · socrata=`Ortofoto. Municipio de Cáqueza del Departamento de Cundinamarca. GSD 10 cm. 2021 (Imagen)`
- `tufb-4h5z` · local=`Ortofoto. Municipio de Quetame. GSD 10 cm. 2021 (Imagen)` · socrata=`Ortofoto. Municipio de Quetame del Departamento de Cundinamarca. GSD 10 cm. 2021 (Imagen)`
- `96bj-i5f8` · local=`Ortofoto. Municipio de Cachipay. GSD 10 cm. 2021 (Imagen)` · socrata=`Ortofoto. Municipio de Cachipay del Departamento de Cundinamarca. GSD 10 cm. 2021 (Imagen)`
- `wv46-xczi` · local=`Ortofoto. Municipio de Topaipí. Escala 2K. 2021 (Imagen)` · socrata=`Ortofoto. Municipio de Topaipí del Departamento de Cundinamarca. Escala 1:2.000. GDS 10 cm. 2021 (Imagen)`
- `hdav-e6y2` · local=`Ortofoto. Municipio de la Palma. GSD 10 cm. 2021 (Imagen)` · socrata=`Ortofoto. Municipio de La Palma del Departamento de Cundinamarca. GSD 10 cm. 2021 (Imagen).`
- `94yp-nhat` · local=`Ortofoto. Municipio de Guayabetal. GSD 10 cm. 2021 (Imagen)` · socrata=`Ortofoto. Municipio de Guayabetal del Departamento de Cundinamarca. GSD 10 cm. 2021 (Imagen).`
- `mnyq-aix3` · local=`Ortofoto. Municipio de Gutiérrez. GSD 10 cm. 2021 (Imagen)` · socrata=`Ortofoto. Municipio de Gutiérrez del Departamento de Cundinamarca. GSD 10 cm. 2021 (Imagen).`

#### description — ejemplos de mismatch (máx 10)
- `dee6-j85w` · local=`<span style='font-family:&quot;Avenir Next W01&quot;, &quot;Avenir Next W00&quot;, &quot;Avenir Next&quot;, Avenir, &quo` · socrata=`<p>La base de datos comprende la sistematización del listado de medidas de manejo asociadas a la internalización, junto `
- `rfju-cn96` · local=`<div style='text-align:Left;font-size:12pt'><div><div><p><span>Contiene datos catastrales geográficos de los municipios ` · socrata=`<div style='font-size:12pt; text-align:Left;'><div><div><p><span>Contiene datos catastrales geográficos y alfanuméricos `
- `wvbg-9pca` · local=`<div style='text-align:Left;font-size:12pt'><div><div><p><span>Contiene datos catastrales geográficos de los municipios ` · socrata=`<div style='font-size:12pt; text-align:Left;'><div><div><p><span>Contiene datos catastrales geográficos y alfanuméricos `
- `st64-2fdr` · local=`<div style='text-align:Left;font-size:12pt'><div><div><p><span>Contiene datos catastrales geográficos de los municipios ` · socrata=`<div style='font-size:12pt; text-align:Left;'><div><div><p><span>Contiene datos catastrales geográficos y alfanuméricos `
- `vnnr-pi5p` · local=`<div style='text-align:Left;font-size:12pt'><div><div><p><span>Contiene datos catastrales geográficos de los municipios ` · socrata=`<div style='font-size:12pt; text-align:Left;'><div><div><p><span>Contiene datos catastrales geográficos y alfanuméricos `
- `6r9y-6qmg` · local=`<div style='text-align:Left;font-size:12pt'><div><div><p><span>Contiene datos catastrales geográficos de los municipios ` · socrata=`<div style='font-size:12pt; text-align:Left;'><div><div><p><span>Contiene datos catastrales geográficos y alfanuméricos `
- `gmsg-eqeu` · local=`<div style='text-align:Left;font-size:12pt'><div><div><p><span>Contiene datos catastrales geográficos de los municipios ` · socrata=`<div style='font-size:12pt; text-align:Left;'><div><div><p><span>Contiene datos catastrales geográficos y alfanuméricos `
- `m89y-879r` · local=`<div style='text-align:Left;font-size:12pt'><div><div><p><span>Contiene datos catastrales geográficos de los municipios ` · socrata=`<div style='font-size:12pt; text-align:Left;'><div><div><p><span>Contiene datos catastrales geográficos y alfanuméricos `
- `vki7-bw45` · local=`<div style='text-align:Left;font-size:12pt'><div><div><p><span>Contiene datos catastrales geográficos de los municipios ` · socrata=`<div style='font-size:12pt; text-align:Left;'><div><div><p><span>Contiene datos catastrales geográficos y alfanuméricos `
- `mik8-c9zh` · local=`<div style='text-align:Left;font-size:12pt'><div><div><p><span>Contiene datos catastrales geográficos de los municipios ` · socrata=`<div style='font-size:12pt; text-align:Left;'><div><div><p><span>Contiene datos catastrales geográficos y alfanuméricos `

#### metadata_updated_at — ejemplos de mismatch (máx 10)
- `hfii-knfn` · local=`2026-05-28 19:11:26+00:00` · socrata=`2026-06-08T19:05:01.000Z`
- `mz9g-zyw5` · local=`2025-07-24 19:10:18+00:00` · socrata=`2026-06-02T19:17:52.000Z`
- `4jum-zayu` · local=`2026-05-28 19:13:24+00:00` · socrata=`2026-06-08T19:13:02.000Z`
- `632p-wvm7` · local=`2026-05-28 19:16:19+00:00` · socrata=`2026-06-08T19:15:56.000Z`
- `6g2y-iw65` · local=`2026-05-28 19:16:15+00:00` · socrata=`2026-06-08T19:15:52.000Z`
- `d6ck-xfhn` · local=`2026-05-28 19:01:51+00:00` · socrata=`2026-06-08T19:01:54.000Z`
- `ajby-ju3v` · local=`2026-05-28 19:11:25+00:00` · socrata=`2026-06-08T19:05:00.000Z`
- `8k9i-ev4h` · local=`2026-05-26 19:05:10+00:00` · socrata=`2026-06-08T19:04:51.000Z`
- `wfw5-p98n` · local=`2026-05-28 19:11:25+00:00` · socrata=`2026-06-08T19:05:00.000Z`
- `x85u-zv33` · local=`2026-05-28 19:04:41+00:00` · socrata=`2026-06-08T19:04:43.000Z`

#### page_views_total — ejemplos de mismatch (máx 10)
- `se7p-ytdd` · local=`3975` · socrata=`4209`
- `wrs4-irpf` · local=`2689` · socrata=`3122`
- `68eb-25rj` · local=`2604` · socrata=`2839`
- `6xpi-v68u` · local=`2396` · socrata=`2567`
- `dx2g-2mhm` · local=`2114` · socrata=`2282`
- `vg4f-q9p9` · local=`1914` · socrata=`2105`
- `5nqi-8tfm` · local=`1793` · socrata=`1933`
- `8fks-vt2s` · local=`1729` · socrata=`1891`
- `ym6c-8zkb` · local=`1689` · socrata=`1876`
- `4h84-62xp` · local=`1614` · socrata=`1743`

#### view_count — ejemplos de mismatch (máx 10)
- `se7p-ytdd` · local=`3975` · socrata=`4209`
- `wrs4-irpf` · local=`2689` · socrata=`3122`
- `68eb-25rj` · local=`2604` · socrata=`2839`
- `6xpi-v68u` · local=`2396` · socrata=`2567`
- `dx2g-2mhm` · local=`2114` · socrata=`2282`
- `vg4f-q9p9` · local=`1914` · socrata=`2105`
- `5nqi-8tfm` · local=`1793` · socrata=`1933`
- `8fks-vt2s` · local=`1729` · socrata=`1891`
- `ym6c-8zkb` · local=`1689` · socrata=`1876`
- `4h84-62xp` · local=`1614` · socrata=`1743`

#### page_views_last_week — ejemplos de mismatch (máx 10)
- `4dai-7crq` · local=`111` · socrata=`124`
- `se7p-ytdd` · local=`121` · socrata=`162`
- `f6du-dwd8` · local=`143` · socrata=`116`
- `nht7-gfb8` · local=`60` · socrata=`57`
- `3itm-5dx4` · local=`34` · socrata=`63`
- `2ie9-7xta` · local=`91` · socrata=`83`
- `wrs4-irpf` · local=`371` · socrata=`267`
- `nzw7-qjkr` · local=`84` · socrata=`77`
- `w66c-tjsq` · local=`66` · socrata=`37`
- `68eb-25rj` · local=`156` · socrata=`174`

#### page_views_last_month — ejemplos de mismatch (máx 10)
- `3itm-5dx4` · local=`147` · socrata=`198`
- `2ie9-7xta` · local=`352` · socrata=`373`
- `nzw7-qjkr` · local=`406` · socrata=`362`
- `47cj-rupe` · local=`243` · socrata=`228`
- `6xpi-v68u` · local=`569` · socrata=`539`
- `dx2g-2mhm` · local=`380` · socrata=`455`
- `vg4f-q9p9` · local=`387` · socrata=`482`
- `ke8u-qixu` · local=`360` · socrata=`307`
- `8yw3-bgcf` · local=`231` · socrata=`260`
- `k8xg-2q2b` · local=`107` · socrata=`114`
