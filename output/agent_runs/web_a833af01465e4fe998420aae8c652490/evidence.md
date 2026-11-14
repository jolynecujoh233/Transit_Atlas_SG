# 文献检索记录

Geographical Accessibility of Community Health Assist Scheme General Practitioners for the Elderly Population in Singapore: A Case Study on the Elderly Living in Housing Development Board Flats
https://www.mdpi.com/1660-4601/15/9/1988
Ong、Chiu 与 Cao（2018）以HDB组屋楼栋为单元，用老年人口、CHAS全科诊所位置及E2SFCA供需可达性方法识别出相对弱可达区域；这直接支持把“老年需求—医疗供给竞争”而非仅站点覆盖作为候选网格的核心筛选维度。可审核初筛可用公开的老年人口空间统计、CHAS诊所名录/地址和路网或公共交通行程时间，逐格保存来源、日期、OD路径和计算脚本。
研究只覆盖居于HDB的老年人和CHAS GP，不等同于综合医院、综合诊疗所或实际就诊需求；每家GP供给被设为1，距离衰减函数也未由本地就诊行为校准。其受限验证输入是当时的楼栋老年人口与CHAS诊所资料，缺少实际预约、候诊、诊疗容量及老年就医OD记录；故只能用于初筛，不可把其函数参数或任何系数当作权重。

The associations between older adults’ daily travel pattern and objective and perceived built environment: A study of three neighbourhoods in Singapore
https://repository.sutd.edu.sg/esploro/outputs/journalArticle/The-associations-between-older-adults-daily/9911258609846
Hou、Yap、Chua、Song 与 Yuen（2020）的同行评审研究以新加坡三个社区老年人的步行、巴士、MRT/LRT和私人机动出行建模，发现感知到的公交邻近性，以及舒适、安全的步行连接，与老年人公共交通出行频率独立正相关。因此，医疗导向候选网格应在公共交通OD时间之外，另列首末段连续性、安全性、遮蔽/舒适性等可审计字段。
样本仅来自三个社区，结果是日常出行关联而非就医出行的因果效应，且部分解释变量为感知调查，不能直接由全岛开放数据复现。初筛可先以公开步道、过街、遮蔽和站点资料作代理指标；这些不能替代对老年就医者的现场审计或问卷验证，也不支持推导指标权重。

Going the Extra Mile: Transport Equity and Healthcare Access for Seniors in Singapore
https://lenezoe.github.io/transportequity-healthcare/index.html
Lee（2023，SUTD已公开核实的学生研究）覆盖226个含65岁以上居民的子区及40处医疗设施，比较公共交通与私车时间/费用，并审计医院最近站点至设施的末段步行；其结果表明，面向老年就医的缺口网格会进一步集中在“到医疗设施公共交通时间较差且末段步行障碍较多”的区域，而不只是公交服务稀疏处。
这是经SUTD项目页可核实的学生项目，并非同行评审论文；公共交通时间取Google Distance Matrix API下七种方式的最快值，且末段审计仅由三名研究者在8所重组医院开展。其受限验证输入还不含真实就医OD、班次拥挤度、候诊容量与无障碍使用者表现；初筛宜用公开设施、站点、线路/时刻与人口资料，之后再用实地无障碍审计和就医行为数据验证。

## 文献综合

相较一般公共交通缺口，老年就医优先情景的候选网格应转向老年人集聚、医疗供给竞争较高、公共交通OD时间较长且首末段障碍突出的地点；Ong等与Lee的研究提供了新加坡本地可复核的供需和路径依据。Hou等与Lee均提示步行连接不可忽略，但三项研究分别受服务范围、三社区样本及非同行评审/有限实测所限，因此方案应公开指标与原始数据版本、先做初筛再验证，且不推定任何数值权重。


## 待补数据来源

研究范围与目录核对结论
https://data.gov.sg/datasets/d_9e035622439b5d25a63d7ea0699c9451/view
原问题可操作化为：新加坡全岛、400米网格、65岁及以上居民，在工作日09:00从居住网格以步行—公共交通到“就医”目的地的可达性/供需缺口。需求应量化每个grid_id的65+常住居民估计数；供给至少量化可作为就医目的地的设施点及其可达数量/时间，扩展时才量化容量与竞争。工作目录中只有输出schema，未提供可读取的指标目录或n_older_residents_65plus、s_chas_clinics_access_30m、s_chas_clinics_access_60m等实际文件；因此不能确认其字段、粒度、覆盖或将其视为已取得。
以下来源只能支撑重新注册或补齐相应指标；需用户提供现有指标文件/数据字典后，才能逐字段核验与复用。

Resident Population by Planning Area/Subzone of Residence, Age Group and Floor Area of Residence (Census of Population 2020)
https://data.gov.sg/datasets/d_9e035622439b5d25a63d7ea0699c9451/view
公开可下载、可追溯。SINGSTAT的2020普查数据有规划区/次区（subzone）及65–69、70–74、75–79、80–84、85–89、90岁及以上年龄字段，可加总为65+。这是需求端的可复用公开汇总来源，适合生成subzone级65+基数，并保留参考年=2020、年龄加总规则、来源与估计/分配方法。最小初筛可将次区总量按透明规则分配至400米网格，但必须另有400米grid_id、几何和面积，并标为“模型估计”而非网格实测人口。
其空间粒度是次区而非400米网格，不能直接验证现有n_older_residents_65plus；更新周期为10年，2020是否可代表研究时点须由用户确认。若改用全岛年度65+总量，只能更新总规模，不能保留小区域差异，属于需用户审核的替代方案。

CHAS Clinics | MOH
https://data.gov.sg/datasets/d_548c33ea2d99e29ec63a7cc9edcccedc/view
公开GEOJSON；页面显示可直接下载，API key只提高限额。设施记录的嵌入属性可解析为HCI_CODE（可作facility_id）、HCI_NAME、LICENCE_TYPE、电话、邮编、楼号/楼层/单元/街道/建筑名、CLINIC_PROGRAMME_CODE、X/Y坐标、FMEL_UPD_D，GeoJSON几何另给经纬度；页面标示数据集最后更新为2024-06-06。它可作为CHAS目的地名录，用于建立facility_id、名称、地址/坐标、CHAS标识、名录版本日期和来源链接。
页面示例中FMEL_UPD_D为2021，和数据集更新日不一致，下载后须逐条核对更新时间与有效性。没有常规门诊开放时段、服务能力、预约量或真实就医量；也不含网格、步行阈值、出发时段、换乘或OD路径。因此不能据此把s_chas_clinics_access_30m/60m认定为公共交通可达性，也不能把“30m/60m”擅自解释成分钟或米。

OneMap Routing API
https://www.onemap.gov.sg/apidocs/routing
SLA的OneMap提供walk与pt路由；pt请求明确需要起终点坐标、date、time、mode，且可设maxWalkDistance、numItineraries，授权token必需。故可在选定真实工作日、09:00，使用400米网格代表点（origin_grid_id）与CHAS的HCI_CODE/坐标组合，记录返回的总时长、分段/首末段、步行距离或时间、换乘和可达标记，计算1–60分钟累计或时间衰减可达性。grid_id是研究方生成键、facility_id来自CHAS，两者能通过坐标与逐OD结果关联；日期/时刻可和每一条OD结果关联。
这是按请求计算的路由结果，不是已下载的观测时间序列，也不是公开GTFS文件；需注册取得token。文档未在已查页面承诺返回字段一定完整覆盖候车、车上时间、换乘数及版本号，批量运行前应以样本响应核验并保存原始响应、查询日期、算法/数据版本和失败记录。若改为只做步行，研究对象就从“公共交通医疗可达性”变为“步行邻近性”，须用户审核。

LTA DataMall Dynamic Datasets
https://datamall.lta.gov.sg/content/datamall/en/dynamic-data.html
LTA页面确认：Bus Stops提供站点代码与坐标；Bus Routes提供在运线路的各站及各站首/末班时间；Bus Services提供首末站与高峰/非高峰发车频率；Bus Arrival是实时ETA；Train GTFS Schedule仅称为计划网络；乘客量按站点或站点OD且仅区分weekday/weekend、按月发布。可把站点坐标、线路与频率登记为s_bus_400m_coverage、s_bus_stop_density、s_route_choice的辅助输入，并明确来源/抓取日。
这些字段不能直接给出某一工作日09:00的完整公交逐班次时刻表；月度weekday/weekend客流也不是09:00服务频次或医疗OD。页面提供“Request for API Access”，故LTA API应归为需注册/申请后核实，而非已取得。不能用Bus Arrival某一瞬间替代时刻表，不能将s_weekday_arrivals_0600_1000外推为09:00单点服务。

Barrier-Free Access API | OneMap
https://www.onemap.gov.sg/apidocs/bfa
SLA说明其无障碍路由为经轮椅使用者测试和验证的路线；可作为“公共交通时间尚可、但首末段可能困难”的补充验证方向。建议登记字段为origin/destination坐标、路线几何与时长、BFA可达/失败状态、审计/查询日和覆盖状态；它可与网格和设施点经坐标关联。
该API仅向获批用户按申请开放，且路由覆盖不足会返回无路由；不是可直接下载的全岛人行道、过街、坡道、台阶、电梯、遮蔽和施工阻断要素库。故应列为中优先级“需申请/仍需核实”，不作为公开初筛前提；真实老年步行可通行性仍需现场审计或使用者验证。

Vaccination_Polyclinics | MOH
https://data.gov.sg/datasets/d_b22489c7dc4065b6e7e45f177fdb33be/view
公开GEOJSON，可作为较窄、可追溯的目的地补充或敏感性样本：字段含OBJECTID、NAME、ADDRESS、POSTALCODE、CONTACTNUMBER、VACCINETYPESANDOPERATINGHOURS、INC_CRC、FMEL_UPD_D及点几何。相比CHAS名录，它含特定服务的开放时段文本，能测试工作日09:00设施是否对该服务开放。
仅为疫苗服务的综合诊疗所子集，不等于全部CHAS GP、医院门诊或专科门诊，不能代表用户尚未界定的“就医”服务范围，更不能提供诊室/医生数、预约可用量、候诊或真实就医OD。E2SFCA/容量竞争应在用户确认目的地范围后，另申请或收集facility_id、容量代理、适用日期及服务对象基数；受限微观资料不应成为公开初筛前提。
