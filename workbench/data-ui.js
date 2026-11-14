const prepState=JSON.parse(sessionStorage.getItem('atlas_processing')||'{}');
let prepProgress='',prepError='';
function savePrep(){sessionStorage.setItem('atlas_processing',JSON.stringify(prepState))}
function choices(items){return items.map(([k,v])=>'<option value="'+esc(k)+'">'+esc(v)+'</option>').join('')}
function preparedCard(p){
 const a=p.aggregation||{};
 return '<h3>'+esc(p.name)+'</h3><p>'+esc(p.operation)+' · '+esc(p.unit)+'</p>'+note('分析代码',a.analysis_code)+'<p class="sm">'+esc(p.raw_rows)+' 条输入记录'+(a.matched_source_rows!=null?'，其中 '+esc(a.matched_source_rows)+' 条匹配研究网格':'')+' → '+esc(p.grid_rows)+' 个唯一网格；无源观测网格 '+esc(a.grids_without_source_observation)+' 个。取值范围 '+esc(p.summary.min)+' 至 '+esc(p.summary.max)+'。</p>'+link(p.source,p.source_name)+'<a download="grid_indicator.csv" href="/api/prepared/'+esc(p.key)+'">下载标准化网格表 ↓</a>';
}
function pipelineHTML(){
 const src=prepState.src,p=prepState.output;
 let top='<div class="kicker">Data preparation</div><h2>数据处理</h2><p class="sm">获取数据 → 统一到 400 米网格 → 审核并计算</p>';
 if(prepProgress)top+='<p class="status" role="status">'+esc(prepProgress)+'</p>';
 if(prepError)top+='<p class="err" role="alert">'+esc(prepError)+'</p>';
 if(p)return top+preparedCard(p)+'<hr><label>情景基础<select id="dataBase">'+choices([['','等权基线'],...(run?.plan.decision==='run'?[[run.id,'当前研究方案']]:[])])+'</select></label><label>新增指标权重<input id="dataWeight" type="number" min=".25" max="3" step="any" value="1"></label><button id="attachData" class="primary">生成待审核方案 →</button><button id="resetData" class="actionlink">重新选择数据</button>';
 if(src){
 const fields=src.profile.columns.map(c=>[c.name,c.name+' · '+c.dtype]);
 const ops=Object.entries(src.operations);
 return top+'<h3>'+esc(src.name)+'</h3><p class="sm">'+esc(src.mode==='download'?'已从官方获取':'已校验项目快照')+' · '+esc(src.profile.row_count)+' 条 · '+esc(src.profile.crs||'表格')+'</p>'+link(src.source,'查看发布页')+(ops.length?
 '<form id="gridForm"><label>指标名称<input name="name" required maxlength="120" placeholder="例如：网格内轨道站出入口数"></label><label>聚合方法<select name="operation">'+choices(ops)+'</select></label><label id="codeRow" hidden>分析代码<input name="analysis_code" maxlength="200" placeholder="count_within(weekday_0900_minutes(), 45)"></label><label id="valueRow">数值字段<select name="field">'+choices(fields)+'</select></label><label>指标单位<input name="unit" required maxlength="80" placeholder="例如：个 / 网格"></label><label>评分方向<select name="direction">'+choices([['higher_is_better','供给 · 值越高供给越好'],['lower_is_better','供给 · 值越低供给越好'],['higher_is_higher_demand','需求 · 值越高需求越高'],['lower_is_higher_demand','需求 · 值越低需求越高']])+'</select></label><label id="factorRow">供给类别<select name="factor">'+choices([['network','网络'],['destinations','目的地'],['frequency','班次'],['flexibility_time','灵活性与时间']])+'</select></label><label>未覆盖网格<select name="missing">'+choices([['error','存在未覆盖网格时停止'],['zero','按 0 处理（须有研究依据）']])+'</select></label><button class="primary">标准化并生成网格表 →</button></form>':
 '<p>当前数据缺少可用的点、面几何或 grid_id。请先完成可信的空间匹配，再纳入网格计算。</p>')+'<button class="actionlink" id="resetData">选择其他数据</button>';
 }
 const available=sources.filter(x=>x.url.includes('/datasets/d_'));
 return top+'<form id="downloadForm"><label>选择项目数据<select id="pickSource"><option value="">选择数据集或粘贴官方链接</option>'+choices(available.map(x=>[x.url,x.name]))+'</select></label><label>data.gov.sg 数据集链接或 ID<input name="dataset" required placeholder="https://data.gov.sg/datasets/d_…/view"></label><label>数据版本<select name="mode">'+choices([['download','下载官方当前版本'],['snapshot','使用并校验项目快照']])+'</select></label><button class="primary">获取数据并检查字段 →</button></form>';
}
function prepRender(){if(view==='processing'){render();$('#side').classList.add('data-panel')}}
async function prepRequest(path,body,field,msg){
 if(prepProgress)return;
 prepError='';prepProgress=msg;const status=document.createElement('p');status.className='status';status.textContent=msg;$('#side').prepend(status);
 try{prepState[field]=await api(path,body);savePrep()}catch(e){prepError=e.message}finally{prepProgress='';prepRender()}
}
function bindDataUI(){
 $('#side').classList.toggle('data-panel',view==='processing');
 if(view!=='processing')return;
 $('#resetData')?.addEventListener('click',()=>{if(prepProgress)return;delete prepState.src;delete prepState.output;prepError='';savePrep();prepRender()});
 const dl=$('#downloadForm');
 if(dl){$('#pickSource').onchange=e=>dl.elements.namedItem('dataset').value=e.target.value;dl.onsubmit=e=>{e.preventDefault();prepRequest('/api/data/download',Object.fromEntries(new FormData(dl)),'src','正在获取源文件并检查结构…')}}
 const grid=$('#gridForm');
 if(grid){const update=()=>{
  const access=grid.elements.operation.value==='access_program';
  $('#codeRow').hidden=!access;
  grid.elements.analysis_code.required=access;
  if(access){grid.elements.factor.value='destinations';grid.elements.direction.value='higher_is_better'}
  $('#valueRow').hidden=access||['point_count','polygon_coverage_share'].includes(grid.elements.operation.value);$('#factorRow').hidden=grid.elements.direction.value.includes('demand')};grid.onchange=update;update();grid.onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(grid));data.key=prepState.src.key;data.side=data.direction.includes('demand')?'demand':'supply';prepRequest('/api/data/prepare',data,'output','正在聚合并校验 1,597 个网格…')}}
 const attach=$('#attachData');
 if(attach){if(run?.plan.decision==='run')$('#dataBase').value=run.id;attach.onclick=()=>{const weight=Number($('#dataWeight').value);if(!Number.isFinite(weight)||weight<.25||weight>3){prepError='权重应在 0.25 至 3 之间';prepRender();return}const payload={key:prepState.output.key,parent:$('#dataBase').value,weight};go('research');job('/api/data/attach',payload,'正在用标准化数据生成待审核方案…')}}
}
