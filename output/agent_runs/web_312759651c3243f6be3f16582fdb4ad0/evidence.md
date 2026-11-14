# 文献检索记录

Understanding short-distance travel to school in Singapore: A data-driven approach
https://www.sciencedirect.com/science/article/pii/S2214367X23000078
新加坡7—18岁学生的实证研究以3,026名住校距离不超过2.5公里的学生为对象；研究用可复现的开放来源构造步行可达性与公交可达性代理指标，发现早高峰出发和更高服务频率与学生选择公共交通有关，学校周边街网连通性则与步行有关。用于候选网格初筛时，可按“居住地—学校”在上学时段的步行接入、站点/线路服务与街网连通性分别制图；不应把这些代理变量直接解释为车辆满载。
验证样本限于距校2.5公里内、且来自众包移动数据的学生；其方式识别不能可靠区分私家车与校车，也没有车辆载客量、班次实际容量或全部学生住址。因此，开放数据足以做可达性初筛，但要验证“供需缺口”仍需分时客流、上/下车或载荷数据。对新加坡的可迁移性很高，因为研究地点、学校通学制度和公交网络均为新加坡；但不能外推到远距离通学者。

Inferring weekly primary activity patterns using public transport smart card data and a household travel survey
https://www.sciencedirect.com/science/article/pii/S2214367X16300588
该新加坡研究以一周CEPAS公交智能卡记录，并用1%家庭出行调查训练学生与就业者的活动类型模型；可依据活动开始时间和持续时间识别“学习”活动，再从连续行程提取通学的时空模式。它为候选网格提供了可审核的需求侧定义：仅汇总被识别为学习活动、且落在实际上学时间窗的起讫行程，而非以全天总客流替代学生需求。
活动类型模型的受限验证输入是1%家庭出行调查和非公开智能卡交易；公开数据通常只能提供学校位置、人口/年龄汇总和时刻/线路，无法复现个体学生识别或检验误分类。因此，公开数据只能形成需求暴露的初筛代理，不能声称得到已验证的学生OD或缺口。对新加坡的可迁移性高，但应以当期学校日历、校址与服务时刻重跑，避免把旧样本时段当作现状。

Smart card data-centric replication of the multi-modal public transport system in Singapore
https://www.tum-create.edu.sg/sites/default/files/files/liu_smart_2018RRT.pdf
Liu、Zhou与Rau以新加坡智能卡数据重建多方式公交运行，将已实现的乘客行程链分配到重建的供给，并报告覆盖约96%的公交出行；产出包括时空需求、换乘模式、时刻表和公交利用率。这支持把“学校上学时段的学生需求”与同一时段、同一路段/站点的供给及利用率分开核验，再识别候选缺口网格。
该方法依赖LTA智能卡数据库及运营资料；其约96%覆盖是公共交通出行覆盖，不是学生群体、潜在未乘公交者或车厢满载度的完整验证，且方法本身明确偏重描述现状而非预测。故开放数据可先以GTFS/站点、校址、路网和人口构造网格筛查；正式缺口判断必须取得分时刷卡、车辆运行与容量/载荷数据。对新加坡的可迁移性直接，但每次服务调整后均须更新运营输入。

## 文献综合

《Understanding short-distance travel to school in Singapore》和《Inferring weekly primary activity patterns using public transport smart card data and a household travel survey》支持把上学时段、学校可达性与学生通学活动分开制图，但其验证分别受限于近校众包样本及非公开调查/智能卡数据。Liu等《Smart card data-centric replication of the multi-modal public transport system in Singapore》说明供给—已实现客流可在新加坡逐时空核验；因此公开数据只能用于可审核的候选网格初筛，不能据此推定满载缺口或给指标赋予数值权重。


## 待补数据来源

LTA DataMall API User Guide & Documentation（v6.11）
https://datamall.lta.gov.sg/content/dam/datamall/datasets/LTA_DataMall_API_User_Guide.pdf?ref=stuartbreckenridge.net
研究对象应保持为“新加坡、审核确定的MOE学校日早高峰内，学生从居住地到学校的公共交通出行需求，与同一时空窗内公交/轨道服务供给和拥挤之间的缺口”。需求的目标量是学生、上车时间、居住起点—学校目的地、方式/换乘链及权重；供给的目标量是按线路—方向—站点—班次的实际兑现运能、上下载和载荷。目录中 n_youth_residents_10_19 只能作为400米居住网格的潜在青年暴露；s_weekday_arrivals_0600_1000 只能作为站点归集后的预计到站频率代理。两者先可回答的较窄问题是：2020年青年居住暴露较高、且06:00–10:00预计到站较少的网格/站点是否空间重叠；不能回答学生实际OD、公交方式份额、座位/站立运能或真实拥挤。DataMall已证实可补充的公开汇总候选是公交站点客流和站点OD：字段分别为 YEAR_MONTH、DAY_TYPE、TIME_PER_HOUR、PT_CODE、TOTAL_TAP_IN_VOLUME、TOTAL_TAP_OUT_VOLUME，以及 YEAR_MONTH、DAY_TYPE、TIME_PER_HOUR、ORIGIN_PT_CODE、DESTINATION_PT_CODE、TOTAL_TRIPS；空间粒度是站点（而非400米格/学校），时间是“月份内的WEEKDAY或WEEKENDS/HOLIDAY、整点”，可用站点代码与站点坐标连接。因此可把它作为最小初筛的第三项：在选定月份，按06:00–10:00将一般公交站点上下车和OD汇总到学校邻近站及居住网格邻近站，识别高需求—低预计班次位置。
这是汇总观测量，不是某个学校日、不是学生标识、没有居住地、学校目的地、卡种、单次行程、扩张权重或完整换乘链；“WEEKDAY”也不能单独排除假期/不同学校日。该指南写明客流文件按月生成、请求日期仅至最近三个月且下载链接15分钟失效；本次只核实了接口与字段，未取得文件、未验证当前账户/密钥要求或历史可得性。故不得把它登记为已取得，亦不能替代最高优先级的学生需求数据。

LTA DataMall Dynamic Datasets
https://datamall.lta.gov.sg/content/datamall/en/dynamic-data.html
最小公开初筛可复用并复核 s_weekday_arrivals_0600_1000 的构造：DataMall列有 Bus Services（服务、首末站及高/离峰发车频率）、Bus Routes（线路站序及每站首末班）、Bus Stops（站点码和坐标）、Bus Arrival（实时预计到站、预计位置、Load）。因此应先把现有指标的站点—网格归集半径/步行规则、方向是否分开、使用的版本日期、06:00–10:00中频率区间如何换算为次数、以及是否仅含公交逐项核验；再以 BusStopCode 连接空间点位。实际供给资料的最高优先级申请清单仍是：服务日、线路/方向、站点、计划与实际到离站、trip/车辆标识、取消/短线、车型与额定容量、逐车或逐站上下载及载荷；计算计划/实际班次、兑现率、可用运能和载荷缺口。
页面明确把 Bus Arrival 标为实时，返回的是未来车辆的预计到站、位置和拥挤等级；它不是可回溯的实际到离站历史，更不是人数载荷。页面所列 GTFS Schedule 和 GTFS Realtime 均为“Train”，不能误写成完整公交GTFS；公交也没有由该页证实的逐班次静态时刻、取消、额定容量或历史实际运行档案。若拟用实时接口，须在选定学校日持续抓取并保存，且仍只能得到 SEA/SDA/LSD 类别而非载客数；当前访问许可状态未核实，不能视为已下载。

MOE：General information of schools（2026）
https://developers.data.gov.sg/datasets?resultId=d_688b934f82c1059ed0a6993d2a829089&topics=education
学校位置/类型可列为公开可下载候选，而非受限学生资料：该CSV有337行、31列，已核实字段包括 School Name、Address、Postal Code、Mrt Desc、Bus Desc、Type Code、Session Code、Mainlevel Code 等，覆盖小学、中学、初级学院等目录学校，年度覆盖为2026且年更。它可用于把学校目的地定位/地理编码、按 Mainlevel Code 划分学段、以 Session Code 标记单/全天制，并把学校与站点或400米格连接；许可页写明采用 Open Data Licence。最小公开初筛组合因而是：既有青年网格暴露＋既有预计到站次数＋此学校目录（必要时再加DataMall月度站点汇总），不应以受限微观学生数据为初筛前置条件。
目录没有学生人数、学生住址、入校时间、逐日开课状态或出行方式；地址/邮编需地理编码后才可与400米格匹配，且数据年度必须与青年网格2020和供给数据版本显式错配说明。不能从 Mainlevel/Session 推断实际学生通学时段或学校容量。

MOE学校日历（Riverside Secondary School 官方网站）
https://www.riversidesec.moe.edu.sg/resources/schoolcalendar/
可先把“学校日”限定为MOE校历中上课的工作日：该校官方页面列出2026年中学学期为1月2日–3月13日、3月23日–5月29日、6月29日–9月4日、9月14日–11月20日，并提示部分年级/考试安排例外。它可用于剔除主要假期并为抽取同一学校日的供需窗口建立日历掩码。若用户接受替代方案，可先审核“常规学期内周二至周四、避开公共假日及各校特殊活动、06:00–10:00”这一初筛窗口；原问题仍保留为“同一具体学校日、按学校实际开始时间”的测量。
这是单校页面，只能佐证MOE校历框架，不能提供全体学校每日是否上课，更没有各校、学段、班级的实际首课时间；JC/MI、私校、特殊教育和考试校的日历可能不同。须向MOE或逐校取得/核对 school_id、日期、是否上课、首课时间、学段后，才可配置精细学校日早高峰权重。

LTA DataMall Static Datasets
https://datamall.lta.gov.sg/content/datamall/en/static-data.html
“Annual Bus Population By Passenger Capacity”已公开列出，但其描述是全新加坡注册公交及一般用途巴士的年度车辆容量分布。它可作为宏观背景或合理性检查，不能用于线路、方向、学校日或站点层面的运能。故精细验证资料应按重要性排序为：(1) 脱敏学生学校日出行/智能卡或调查记录；(2) 同日运营方/LTA的实际车辆运行、车型额定容量、取消/短线和逐站上下车/载荷；(3) 学校日历及开课时间；(4) 如做可达性，再要可步行网络、站点/时刻和学校点。每项均应在取得前标注“需注册/申请或尚未核实”，而非已取得。
年度注册车辆容量既不识别公共线路投放，也没有车辆排班、实际运营、乘客载荷或学校日时间戳，不能与400米青年网格直接结合来计算供需缺口。

Singapore Land Authority：National Map Line
https://data.gov.sg/datasets?query=map&resultId=d_10480c0b59e65663dfae1028ff4aa8bb
可达性初筛的公开空间候选是该GEOJSON：官方说明它含全国地图的线状要素，包括快速路、主要道路、国界和等高线，页面标明可下载并采用开放数据许可。它可作底图或补充道路连通性检查，并与学校/站点点位和400米网格叠加。
已核实的属性只有OBJECTID、NAME、FOLDERPATH、SYMBOLID等，且说明是“主要”线要素；尚未证明它是可路由、完整的人行网络，也没有人行规则、过街、坡度、步速、换乘惩罚或公交逐班次时刻。因此不能直接计算题述1–60分钟步行+公交可达性；这些参数和合适的步行/时刻数据须由用户审核并另行取得。
