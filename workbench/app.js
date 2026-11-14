const $ = s => document.querySelector(s);
const t = text => (window.I18n ? window.I18n.t(text) : text);
const esc = v => String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const example='senior_chas_question_only_v1', historyId='senior_chas_review_v1';
let view='overview',run=null,result=null,busy=false,notice='',failed=false,sources=[],draft='',edits={};
let turns=JSON.parse(sessionStorage.getItem('atlas_turns')||'[]');
let layers={areas:true,routes:true,network:true,grids:true},zoom=1;
const fieldInfo={
 n_older_residents_65plus:['65 岁及以上居民人数','age by geography'],
 n_youth_residents_10_19:['10–19 岁居民人数','age by geography'],
 n_low_income_households_lt3000:['月收入低于 3,000 新元的家庭','household income'],
 n_non_car_commuters:['非私家车通勤人数','commute mode and bus use'],
 n_unemployed_residents:['失业居民人数','labour force status'],
 n_low_education_residents_15plus:['低学历居民人数','education'],
 n_one_person_households:['一人家庭数','household size'],
 n_mobility_difficulty_residents_5plus:['行动困难居民人数','activity difficulty'],
 n_public_transit_users_work_school_sum:['公共交通上学或通勤人数','student travel mode','commute mode and bus use'],
 s_chas_clinics_access_30m:['30 分钟 CHAS 诊所可达性','CHAS clinic points','routing'],
 s_chas_clinics_access_60m:['60 分钟 CHAS 诊所可达性','CHAS clinic points','routing'],
 s_bus_400m_coverage:['400 米公交站覆盖率','bus stop points'],
 s_bus_stop_density:['公交站密度','bus stop points'],
 s_low_income_work_access_30m:['30 分钟低收入就业可达性','workplace area by income','routing'],
 s_low_income_work_access_60m:['60 分钟低收入就业可达性','workplace area by income','routing'],
 s_supermarkets_access_30m:['30 分钟超市可达性','routing'],
 s_route_choice:['工作日公交线路选择','routing','bus stop points'],
 s_weekend_arrivals_0900_1600:['周末日间预计到站班次','bus stop points'],
 s_weekday_arrivals_0600_1000:['工作日早高峰预计到站班次','bus stop points'],
 s_weekday_arrivals_0000_0500:['工作日凌晨预计到站班次','bus stop points']
};
const titles={processing:['数据处理','将公开数据转换为可核验的网格指标，审核后再纳入情景计算。','DATA'],overview:['新加坡公共交通供需图谱','在 400 米网格上，对照出行需求与公共交通供给。','OVERVIEW'],research:['研究对话','提出研究问题，核对证据，再决定哪些参数进入计算。','RESEARCH'],results:['情景对照','逐格查看相对等权基线保留、新增与退出的候选地区。','COMPARISON']};
async function api(path,body){
 const res=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
 const data=await res.json(); if(!res.ok)throw Error(data.error||'请求失败');return data;
}
function link(url,text){try{if(!['https:','http:'].includes(new URL(url).protocol))return ''}catch{return ''}return '<a class="cardlink" href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(text)+' ↗</a>'}
function map(){
 const res=view==='results'?result:null;
 $('#mapMode').textContent=res?t('情景对照'):t('基线视图');
 const classes=res?[['retained',t('保留')],['entered',t('新增')],['exited',t('退出')]]:[['baseline',t('基线候选')],['grids',t('研究网格')]];
 $('#legend').innerHTML=classes.map(([key,label])=>'<i style="background:var(--atlas-'+key+')"></i>'+label).join(' ');
 window.drawAtlas($('#atlas'),{layers:{...layers},zoom,changes:res?.changes||null,onPick(cell){
 const el=$('#picked');el.hidden=!cell;if(cell)el.textContent=cell.area+' · '+cell.grid_id+' · '+({retained:'保留',entered:'新增',exited:'退出',neither:'均未入选'}[cell.change]||(cell.candidate?'基线候选':'研究网格'));
 }}).catch(e=>{$('#picked').hidden=false;$('#picked').textContent='地图加载失败：'+e.message});
}
function go(next){view=next;location.hash=next;document.body.classList.toggle('research-mode',next==='research');
 document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===next));
 const tArr=titles[next];$('#title').innerHTML=t(tArr[0])+'<span>.</span>';$('#subtitle').textContent=t(tArr[1]);$('#crumb').textContent=tArr[2];$('#picked').hidden=true;render();map();}
function overview(){
 return '<div class="kicker">Research agent</div><h2><span data-i18n="情景研究入口">情景研究入口</span></h2><p><span data-i18n="输入一个交通公平性问题，查看模型建议的指标、文献与数据来源。">输入一个交通公平性问题，查看模型建议的指标、文献与数据来源。</span></p><hr><div class="metric"><span><span data-i18n="需求侧指标">需求侧指标</span></span><strong>09</strong></div><div class="meter"><b style="width:45%;background:#ba95fb"></b></div><div class="metric"><span><span data-i18n="供给侧指标">供给侧指标</span></span><strong>11</strong></div><div class="meter"><b style="width:55%;background:#66cfcb"></b></div><hr><button class="primary" id="enter"><span data-i18n="进入研究对话">进入研究对话</span> <span>↗</span></button><button class="actionlink" id="sample"><span data-i18n="查看已有提案 · 老年人就医 →">查看已有提案 · 老年人就医 →</span></button>';
}
function stats(items){return '<div class="stats">'+items.map(([n,s])=>'<div class="stat"><b>'+esc(n)+'</b><span>'+esc(s)+'</span></div>').join('')+'</div>'}
function changelist(){return run?[...run.plan.demand_changes.map(c=>({...c,side:'需求'})),...run.plan.supply_changes.map(c=>({...c,side:'供给'}))]:[]}
function noteRecords(text){
 const records=[];
 for(const block of text.trim().split(/\r?\n\s*\r?\n/)){
   const lines=block.trim().split(/\r?\n/);
   const at=lines.findIndex(line=>/https?:\/\//.test(line));
   if(at<0||lines[0].startsWith('#'))continue;
   const url=lines[at].match(/https?:\/\/[^\s)\]]+/)[0];
   const inline=lines[at].replace(/\[[^\]]+\]\(https?:\/\/[^)]+\)/g,'').replace(url,'').trim();
   const finding=at>0?lines.slice(at+1,at+2).join(''):(inline||lines[1]||'');
   records.push({url,title:at>0?lines.slice(0,at).join(' '):inline.split(/[。；]/)[0]||'原始研究',
     finding,limit:lines.slice(at>0?at+2:(inline?1:2)).join(' ')});
 }
 return records;
}
function detail(name,status,body,reason=''){
 const description=reason?'<span class="data-reason">'+esc(reason)+'</span>':'';
 return '<details class="proposal-row"><summary><span>'+esc(name)+'</span><small>'+esc(status)+'</small>'+description+'</summary><div class="row-body">'+body+'</div></details>';
}
function note(label,value){
 return value?'<p><strong>'+esc(label)+'</strong> '+esc(value)+'</p>':'';
}
function indicatorName(id){
 return fieldInfo[id]?.[0]||run.prepared_inputs?.find(p=>p.indicator===id)?.name||id;
}
function indicatorSources(id){
 const purposes=fieldInfo[id]?.slice(1)||[];
 const matched=sources.filter(s=>purposes.includes(s.purpose)).map(s=>link(s.url,s.name));
 if(id.includes('arrivals'))for(const name of ['BusRoutes','BusServices']){
   matched.push(link('https://github.com/Vorld/singapore-gtfs/blob/main/data/raw/datamall-bus/'+name+'.csv','LTA '+name+' 数据快照'));
 }
 if(id==='s_supermarkets_access_30m')matched.push(link('https://www.sfa.gov.sg/tools-and-resources/track-records','SFA 超市许可记录'));
 return matched.join('')||'<p>这项指标尚未附上可核对的来源链接。</p>';
}
function selectedDownloads(){
 const offer=run.data_offer;
 const checked=JSON.parse(sessionStorage.getItem('atlas_selection_'+offer.revision)||'[]');
 const done=new Set((run.partial_inputs||[]).map(p=>p.offer_index));
 return checked.filter(i=>Number.isInteger(i)&&i>=0&&(i<offer.items.length||run.gap_results?.[i-offer.items.length]?.file)&&!done.has(i));
}
function selectedSearches(){
 return JSON.parse(sessionStorage.getItem('atlas_search_'+run.data_offer.revision+'_'+run.search_version)||'[]');
}
const gapStatuses={download:'已找到可下载数据',restricted:'来源需授权',limited:'仅部分匹配',method:'已有方法建议',not_found:'未找到匹配来源'};
const priorityLabels={required:'必须补充',recommended:'建议补充',optional:'可选补充'};
function supplementRows(offer){
 const rows=[];
 const ranked=run.data_priorities||[
   ...offer.items.map((item,i)=>({key:'file:'+i,title:item.name})),
   ...offer.unresolved.map((text,i)=>({key:'gap:'+i,title:text.split(/[：:，。；]/)[0]}))
 ];
 const done=new Map((run.partial_inputs||[]).map(p=>[p.offer_index,p]));
 const downloads=selectedDownloads(),searches=selectedSearches();
 for(const r of ranked){
   const [kind,number]=r.key.split(':'),i=Number(number);
   const found=kind==='gap'?run.gap_results?.[i]:null;
   const item=kind==='file'?offer.items[i]:found?.file;
   const fileIndex=kind==='file'?i:offer.items.length+i;
   const output=done.get(fileIndex);
   const route=output?'网格表已就绪':found?gapStatuses[found.status]:item?'可自动下载':'交给 Agent 检索';
   const reason=r.with_data||item?.reason||'';
   let body=found?note('来源说明',found.finding):'';
   if(item){
     const method=item.method+(item.field?'，使用字段 '+item.field:'')+'。单位为'+item.unit+'。无观测网格'+(item.missing==='zero'?'计为 0。':'出现时停止处理。');
     body+=note('处理方法',method)+note('待审核的分析代码',item.analysis_code)+note('局限',item.limitation)+link(item.source,item.title+' · 官方下载页');
     if(output)body+=preparedCard(output);
   }else if(!found)body+=note('待核对',offer.unresolved[i]);
   if(found)body+=found.sources.filter(s=>s.url!==item?.source).map(s=>link(s.url,s.title)).join('');
   if(r.priority==='optional'||r.priority==='recommended')body+=note('跳过的影响',r.without_data);
   if(found?.status==='method')body+='<button class="ghost" data-method="'+i+'" '+(busy?'disabled':'')+'>采用方法建议，重新评估提案 →</button>';
   if(found?.alternative)body+=note('替代问题',found.alternative)+'<button class="ghost" data-alternative="'+i+'" '+(busy?'disabled':'')+'>用这个问题生成新提案 →</button>';
   const action=item?'选择下载 ':found?'让 Agent 再次检索 ':'让 Agent 检索 ';
   const checked=output||(item?downloads.includes(fileIndex):searches.includes(i));
   const box='<label class="download-check"><input type="checkbox" '+(item?'data-download="'+fileIndex:'data-search="'+i)+'" aria-label="'+esc(action+r.title)+'" '+(checked?'checked ':'')+(busy||output?'disabled':'')+'></label>';
   rows.push('<article class="supplement"><div class="download-row">'+box+
     detail(r.title,(priorityLabels[r.priority]||'待评估')+' · '+route,body,reason)+'</div></article>');
 }
 return rows;
}
function proposalData(datasetNotes){
 const changes=changelist();
 const offer=run.data_offer;
 const prepared=run.prepared_inputs||[];
 const rows=offer?supplementRows(offer):[];
 for(const p of prepared){
   const why=changes.find(c=>c.indicator_id===p.indicator)?.reason;
   rows.push(detail(p.name,'已标准化',note('选用理由',why||'该指标已列入本轮情景。')+preparedCard(p)));
 }
 for(const c of changes.filter(c=>!prepared.some(p=>p.indicator===c.indicator_id))){
   rows.push(detail(indicatorName(c.indicator_id),c.side+' · 已有',note('选用理由',c.reason)+indicatorSources(c.indicator_id)));
 }
 const missing=offer?[]:run.plan.data_needed;
 for(const text of missing){
   const boundary=text.search(/[：:，。；]/);
   const title=boundary>1?text.slice(0,boundary):text;
   rows.push(detail(title,'待补充',note('尚缺什么',text)));
 }
 const refs=[];
 for(const ref of datasetNotes){
   if(offer?.items.some(i=>i.source===ref.url)||prepared.some(p=>p.source===ref.url))continue;
   refs.push(detail(ref.title,'',note('相关数据与用途',ref.finding)+note('获取与使用限制',ref.limit)+link(ref.url,'查看来源')));
 }
 if(refs.length)rows.push(detail('补充数据的参考来源',refs.length+' 个',refs.join('')));
 const rest=Object.keys(fieldInfo).filter(id=>!changes.some(c=>c.indicator_id===id));
 if(rest.length){
   const entries=rest.map(id=>detail(indicatorName(id),id.startsWith('n_')?'需求侧':'供给侧',note('纳入原因','基线指标，按默认权重 1 参与综合评分。')+indicatorSources(id))).join('');
   rows.push(detail('沿用基线的数据指标','共 '+rest.length+' 项',entries));
 }
 return rows.join('');
}
function literature(records){
 if(!records.length)return '<p>本版提案没有附可核对的文献。可以在修改要求里指定需要补查的研究。</p>';
 return records.map(r=>{
   const lead=r.finding.match(/^.*?[。！？](?:[”’])?/)?.[0]||r.finding;
   return '<article class="paper"><strong>'+esc(r.title)+'</strong>'+note('文献要点',lead)+
    ((lead!==r.finding||r.limit)?'<details><summary>适用性与局限</summary>'+note('与本研究的关系',r.finding.slice(lead.length).trim())+note('局限',r.limit)+'</details>':'')+
    link(r.url,'查看文献原文')+'</article>';
 }).join('');
}
function weightReview(){
 const weights=changelist().map(c=>{
   const extension=run.plan.use_registered_indicators.includes(c.indicator_id);
   return '<div class="weight"><strong>'+esc(indicatorName(c.indicator_id))+'</strong><label>'+c.side+(extension?' · 新增指标权重 ':' · 基线 1 → ')+'<input type="number" min=".25" max="3" step="any" aria-label="'+esc(indicatorName(c.indicator_id))+' 权重" data-weight="'+esc(c.indicator_id)+'" value="'+esc(edits[c.indicator_id]??c.weight)+'"></label>'+note('理由',c.reason)+'</div>';
 }).join('');
 return '<h3 id="weightTitle" tabindex="-1">审核情景权重</h3>'+(weights||'<p>本轮采用默认权重 1。</p>')+
  '<button class="primary" id="approve" '+(busy?'disabled':'')+'>确认权重并运行情景 →</button>';
}
function selectionAction(){
 const offer=run.data_offer, files=selectedDownloads(),searches=selectedSearches();
 const ready=new Set((run.partial_inputs||[]).map(p=>p.offer_index<offer.items.length?'file:'+p.offer_index:'gap:'+(p.offer_index-offer.items.length)));
 const required=run.data_priorities?.filter(r=>r.priority==='required').map(r=>r.key)||
   [...offer.items.map((_,i)=>'file:'+i),...offer.unresolved.map((_,i)=>'gap:'+i)];
 const blocked=required.some(key=>!ready.has(key));
 const parts=[];
 if(files.length)parts.push('下载 '+files.length+' 项');
 if(searches.length)parts.push('Agent 检索 '+searches.length+' 项');
 let caption=parts.length?'确认选择（'+parts.join('，')+'）':'请先勾选要检索或下载的项目';
 if(!parts.length&&!blocked)caption='使用已就绪的数据，生成权重建议';
 return {caption,disabled:busy||(!parts.length&&(blocked||Boolean(run.next_run)))};
}
function proposalAction(){
 const disabled=busy?' disabled':'';
 if(run.status==='completed')return '<button class="primary" id="showResult">查看本次情景结果 →</button>';
 if(run.status==='awaiting_review'){
   if(run.prepared_inputs?.length||sessionStorage.getItem('atlas_review_id')===run.id)return weightReview();
   return '<p>本轮所需的网格指标已就绪，确认提案后即可核对模型建议的权重。</p><button class="primary" id="reviewWeights"'+disabled+'>确认提案，进入权重审核 →</button>';
 }
 const offer=run.data_offer;
 if(!offer)return note('数据建议',run.data_offer_error||'需要先核对数据来源与标准化方法。')+'<button class="primary" id="suggestData"'+disabled+'>核对来源并生成处理方案 →</button>';
 const choice=selectionAction();
 let action=note('下一步','Agent 自动检索必需项。你也可以勾选可选项或再次检索。确认下载后，Agent 会把支持的数据处理成网格指标。');
 if(run.partial_error)action+=note('上次处理未完成',run.partial_error);
 action+='<button class="primary" id="confirmData"'+(choice.disabled?' disabled':'')+'>'+esc(choice.caption)+' →</button>';
 if(run.next_run)action+='<button class="ghost" id="openPrepared">查看后续提案 →</button>';
 return action+'<button class="actionlink" id="suggestData"'+disabled+'>重新核对数据来源</button>';
}
const proposalSections={idea:'研究思路',data:'建议清单',literature:'文献与总结'};
function sectionButtons(){
 if(!run)return '';
 return '<div class="proposal-sections" role="group" aria-label="提案栏目">'+Object.entries(proposalSections).map(([id,label])=>
   '<button type="button" data-section="'+id+'" aria-controls="section-'+id+'">'+label+'</button>').join('')+'</div>';
}
function showSection(id){
 if(!Object.hasOwn(proposalSections,id))id='idea';
 document.querySelectorAll('[data-section]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.section===id)));
 document.querySelectorAll('[data-panel]').forEach(p=>p.hidden=p.dataset.panel!==id);
}
function proposal(){
 if(!run)return '';
 const sections=(run.evidence||'').split(/^## (.+?)\s*$/gm);
 const refs=noteRecords(sections[0]);
 let datasetNotes=[],synthesis='';
 for(let i=1;i<sections.length;i+=2){
   if(sections[i]==='待补数据来源')datasetNotes=noteRecords(sections[i+1]);
   if(sections[i]==='文献综合')synthesis=sections[i+1].trim();
 }
 const limits=run.plan.limitations;
 return '<section class="proposal-block" id="section-idea" data-panel="idea"><h3>研究思路</h3><div class="message">'+esc(run.plan.research_question)+'</div>'+
 (run.plan.approach_summary?'<p>'+esc(run.plan.approach_summary)+'</p>':'')+
 (limits.length?detail('研究限制','',limits.map(t=>'<p>'+esc(t)+'</p>').join('')):'')+'</section>'+
 '<section class="proposal-block" id="section-data" data-panel="data"><h3>建议数据清单</h3><p class="sm">'+(run.data_priorities?'按对研究问题的重要性排列。勾选本轮要补充的项目，展开查看来源和获取方法。':'展开数据项查看来源和理由。')+'</p>'+proposalData(datasetNotes)+'</section>'+
 '<section class="proposal-block" id="section-literature" data-panel="literature"><h3>文献与总结</h3>'+note('综合结论',synthesis)+literature(refs)+'</section>'+
 '<section class="proposal-action" id="proposalAction" tabindex="-1">'+proposalAction()+'</section>';
}
function research(){
 let status=notice?'<p class="status '+(failed?'err':'')+'" role="status">'+esc(notice)+'</p>':'';
 const thread=turns.length?'<details class="thread"><summary>对话记录 · '+turns.length+' 轮</summary>'+turns.map(t=>'<div class="message"><small>研究者</small><br>'+esc(t.question)+'</div>'+(t.reply?'<p class="sm"><strong>Agent</strong> · '+esc(t.reply)+'</p>':'')).join('')+'</details>':'';
 const prompt=run?'写下本版提案需要修改的内容，可指定数据项、补充来源链接或调整研究范围。':'例如：优先考虑老年人就医时，哪些地区的公共交通供需缺口更突出？';
 return '<div class="kicker">Research dialogue</div><div class="proposal-heading"><h2>'+(run?'情景提案':'你的研究问题')+'</h2>'+(run?'<button class="ghost" id="nextAction">前往下一步 ↓</button>':'')+'</div>'+sectionButtons()+status+thread+proposal()+
 '<hr><form id="ask"><label for="question">'+(run?'修改这份提案':'想研究什么？')+'</label><textarea id="question" required maxlength="1500" placeholder="'+esc(prompt)+'">'+esc(draft)+'</textarea><div class="actions"><button class="ghost" type="submit" '+(busy?'disabled':'')+'>'+(run?'提交修改要求':'发送研究问题')+' ↗</button>'+(!run?'<button class="ghost" id="sample" type="button">查看已有提案</button>':'')+'</div></form>';
}
function results(){
 if(!result)return '<div class="kicker">Scenario comparison</div><h2>读取结果</h2>';
 return '<div class="kicker">Scenario comparison</div><h2>候选网格变化</h2><p>'+esc(result.plan.research_question)+'</p><hr><div class="metric"><span>等权基线 → 本次情景</span><strong>148 → '+result.candidate_count+'</strong></div>'+stats([[result.retained,'保留'],[result.entered,'新增'],[result.exited,'退出']])+(result.prepared_inputs||[]).map(preparedCard).join('')+'<hr><p class="sm">点击地图网格查看地区和入选状态。逐格得分与等级可在对照表中核查。</p><a class="actionlink" download="baseline_comparison.csv" href="/api/export/'+result.id+'">下载逐网格对照表 ↓</a>';
}
function render(){
 $('#side').innerHTML=view==='overview'?overview():view==='research'?research():view==='processing'?pipelineHTML():results();
 $('#lower').innerHTML=view==='overview'?stats([['1,597',t('正估计人口研究网格')],['400 m',t('网格空间分辨率')],['148',t('基线候选网格')]]):'';
 if(window.I18n){window.I18n.apply($('#side'));window.I18n.apply($('#lower'));}
 bindDataUI();
 $('#enter')?.addEventListener('click',()=>{
   if(!busy){run=null;draft='';edits={};turns=[];notice='';failed=false;sessionStorage.removeItem('atlas_turns');sessionStorage.removeItem('atlas_run')}
   go('research');
 });
 $('#sample')?.addEventListener('click',()=>loadRun(example));
 $('#nextAction')?.addEventListener('click',()=>$('#proposalAction').focus());
 if(run&&view==='research'){
   const key='atlas_section_'+run.id;
   showSection(sessionStorage.getItem(key)||'idea');
   document.querySelectorAll('[data-section]').forEach(b=>b.onclick=()=>{
     sessionStorage.setItem(key,b.dataset.section);showSection(b.dataset.section);
   });
 }
 document.querySelectorAll('[data-alternative]').forEach(b=>b.onclick=()=>{
   draft=run.gap_results[b.dataset.alternative].alternative;
   $('#question').value=draft;if(draft.length<=1500)$('#ask').requestSubmit();else $('#question').focus();
 });
 document.querySelectorAll('[data-method]').forEach(b=>b.onclick=()=>{
   const i=b.dataset.method;
   draft='采用缺口「'+(run.data_priorities?.find(r=>r.key==='gap:'+i)?.title||run.data_offer.unresolved[i].slice(0,100))+'」的 Agent 检索方法建议。请结合现有数据重新评估原研究问题，说明哪些指标可计算、哪些仍缺输入。';
   $('#question').value=draft;$('#ask').requestSubmit();
 });
 document.querySelectorAll('[data-download],[data-search]').forEach(box=>box.onchange=()=>{
   const indices=Array.from(document.querySelectorAll('[data-download]:checked:not(:disabled)'),b=>Number(b.dataset.download));
   const searches=Array.from(document.querySelectorAll('[data-search]:checked'),b=>Number(b.dataset.search));
   sessionStorage.setItem('atlas_selection_'+run.data_offer.revision,JSON.stringify(indices));
   sessionStorage.setItem('atlas_search_'+run.data_offer.revision+'_'+run.search_version,JSON.stringify(searches));
   const confirm=$('#confirmData');
   const action=selectionAction();
   if(confirm){confirm.disabled=action.disabled;confirm.textContent=action.caption+' →'}
 });
 $('#suggestData')?.addEventListener('click',()=>job('/api/data/suggest',{id:run.id},'正在核对来源与标准化方法…'));
 $('#confirmData')?.addEventListener('click',()=>job('/api/data/confirm',{id:run.id,revision:run.data_offer.revision,priority_version:run.priority_version,search_version:run.search_version,selected:selectedDownloads(),search:selectedSearches()},'Agent 正在处理所选项目…'));
 $('#openPrepared')?.addEventListener('click',()=>loadRun(run.next_run));
 $('#reviewWeights')?.addEventListener('click',()=>{sessionStorage.setItem('atlas_review_id',run.id);render();$('#weightTitle')?.focus()});
 $('#showResult')?.addEventListener('click',()=>{result=run;sessionStorage.setItem('atlas_result',run.id);go('results')});
 document.querySelectorAll('[data-weight]').forEach(el=>el.oninput=()=>{edits[el.dataset.weight]=el.value});
 $('#question')?.addEventListener('input',e=>draft=e.target.value);
 $('#ask')?.addEventListener('submit',e=>{e.preventDefault();if(!draft.trim()||busy)return;turns.push({question:draft});sessionStorage.setItem('atlas_turns',JSON.stringify(turns));job('/api/propose',{question:draft.trim(),parent:run?.id},'正在检索文献并生成提案，可能需要几分钟。')});
 $('#approve')?.addEventListener('click',()=>{
 const updated={};for(const c of changelist()){const raw=edits[c.indicator_id]??c.weight,v=Number(raw);if(raw===''||!Number.isFinite(v)||v<.25||v>3){notice='权重须为 0.25 至 3 之间的数值。';failed=true;render();return}if(v!==c.weight)updated[c.indicator_id]=v}
 job('/api/approve',{id:run.id,edits:updated},'已确认，正在对全部 1,597 个网格计算并与基线对照。')});
}
async function loadRun(id){if(busy)return;try{run=await api('/api/run/'+id);edits={};draft='';failed=false;notice=run.status==='awaiting_review'?'待研究者审核':run.status==='completed'?'该提案已完成计算':'需要补充数据';sessionStorage.setItem('atlas_run',id);go('research')}catch(e){notice=e.message;failed=true;go('research')}}
async function monitor(id){
 while(true){await new Promise(r=>setTimeout(r,1800));const data=await api('/api/run/'+id);if(data.status==='working'){if(data.stage&&notice!==data.stage){notice=data.stage;render()}continue}if(data.status==='failed')throw Error(data.error);
 if(data.next_run&&!data.partial_error){id=data.next_run;continue}
 busy=false;failed=false;draft='';edits={};sessionStorage.removeItem('atlas_job');run=data;sessionStorage.setItem('atlas_run',id);
 if(turns.length&&data.status!=='completed'){turns[turns.length-1].reply=data.plan.rationale;sessionStorage.setItem('atlas_turns',JSON.stringify(turns))}
 if(data.status==='completed'){result=data;sessionStorage.setItem('atlas_result',id);notice='情景计算已完成';go('results')}else{notice=data.status==='needs_data'?'本轮研究有数据缺口，请核对下方建议。':data.prepared_inputs?.length?'网格指标已就绪，请审核权重后再计算。':'模型已提交提案，等待你审核。';go('research')}break;}
}
async function job(path,payload,msg){if(busy)return;busy=true;failed=false;notice=msg;render();try{const {id}=await api(path,payload);sessionStorage.setItem('atlas_job',id);await monitor(id)}catch(e){busy=false;failed=true;notice='任务未完成：'+e.message;sessionStorage.removeItem('atlas_job');go('research')}}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>go(b.dataset.view));
document.querySelector('.brand').onclick=e=>{e.preventDefault();go('overview')};
window.addEventListener('hashchange',()=>{const v=location.hash.slice(1);if(v in titles&&v!==view)go(v)});
document.querySelectorAll('[data-layer]').forEach(b=>b.onclick=()=>{layers[b.dataset.layer]=!layers[b.dataset.layer];b.setAttribute('aria-pressed',layers[b.dataset.layer]);map()});
$('#zoomin').onclick=()=>{zoom=Math.min(5,zoom*1.4);map()};$('#zoomout').onclick=()=>{zoom=Math.max(1,zoom/1.4);map()};$('#reset').onclick=()=>{zoom=1;map()};
(async()=>{try{[sources,result]=await Promise.all([api('/api/sources'),api('/api/run/'+(sessionStorage.getItem('atlas_result')||historyId))]);const prior=new URLSearchParams(location.search).get('run')||sessionStorage.getItem('atlas_run');if(prior){const previous=await api('/api/run/'+encodeURIComponent(prior));if(previous.plan)run=previous;if(run?.status==='awaiting_review')notice='待研究者审核';}
 const pending=sessionStorage.getItem('atlas_job');if(pending){busy=true;notice='正在读取研究任务进度。';go('research');await monitor(pending)}else{go(titles[location.hash.slice(1)]?location.hash.slice(1):'overview')}
 }catch(e){busy=false;sessionStorage.removeItem('atlas_job');failed=true;notice=e.message;go('research')}})();


function bindHelpModal(){
 const modal=$('#helpModal');
 const openBtn=$('#openHelp');
 const closeBtn=$('#closeHelp');
 if(!modal)return;
 if(openBtn)openBtn.onclick=()=>{modal.showModal();if(window.I18n)window.I18n.apply(modal);};
 if(closeBtn)closeBtn.onclick=()=>modal.close();
 modal.addEventListener('click',e=>{if(e.target===modal)modal.close();});
}
bindHelpModal();
window.addEventListener('languagechange',()=>{
 const tArr=titles[view];
 if(tArr){$('#title').innerHTML=t(tArr[0])+'<span>.</span>';$('#subtitle').textContent=t(tArr[1]);}
 render();
 map();
});
