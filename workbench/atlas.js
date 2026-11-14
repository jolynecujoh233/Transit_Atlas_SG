/* Local cartography in Singapore TM (EPSG:3414), metres. */
(() => {
  const asset = new URL('atlas.json', document.currentScript.src);
  let loading;
  const contexts = new WeakMap();
  const labelAreas = ['WOODLANDS','YISHUN','PUNGGOL','JURONG WEST','BUKIT PANJANG','ANG MO KIO','BEDOK','DOWNTOWN CORE','CHANGI','TUAS'];
  const slot = (col,row) => col + ',' + row;
  function prepare(data) {
    const shape = rings => {
      const path = new Path2D();
      for (const ring of rings) {
        path.moveTo(ring[0],ring[1]);
        for (let i=2;i<ring.length;i+=2) path.lineTo(ring[i],ring[i+1]);
        path.closePath();
      }
      return path;
    };
    data.busRouteShape = new Path2D();
    for (const line of data.busRoutes) {
      data.busRouteShape.moveTo(line[0], line[1]);
      for (let i = 2; i < line.length; i += 2) {
        data.busRouteShape.lineTo(line[i], line[i+1]);
      }
    }
    data.areaShapes = data.areas.map(shape);
    data.zoneShape = shape(data.zones.flat());
    data.coverShapes = [0,1].map(type => shape(data.cover.filter(row=>row[0]===type).flatMap(row=>row[1])));
    data.byCell = new Map(data.grids.map(([col,row,area,candidate,demand,deficit])=>[
      slot(col,row),{col,row,grid_id:'SG400_E'+String(col).padStart(4,'0')+'_N'+String(row).padStart(4,'0'),area,candidate:!!candidate,demand,deficit}
    ]));
    return data;
  }
  function initialize(canvas) {
    const state={options:{},data:null,pan:[0,0],view:null,drag:null,frame:0};
    const styles=getComputedStyle(canvas);
    state.colors=Object.fromEntries(['areas','routes','network','grids','baseline','retained','entered','exited']
      .map(key=>[key,styles.getPropertyValue('--atlas-'+key).trim()]));
    const queue=()=>{ if (!state.frame) state.frame=requestAnimationFrame(()=>{state.frame=0;render(canvas,state)}); };
    state.observer=new ResizeObserver(queue);
    state.observer.observe(canvas);
    canvas.addEventListener('pointerdown', event=>{
      if (event.button!==0) return;
      state.drag={x:event.clientX,y:event.clientY,px:state.pan[0],py:state.pan[1],moved:false};
      if(canvas.setPointerCapture) canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', event=>{
      const d=state.drag;
      if(!d || !state.view) return;
      const dx=event.clientX-d.x, dy=event.clientY-d.y;
      if(Math.hypot(dx,dy)>4)d.moved=true;
      if(d.moved && state.options.zoom>1) {
        const limit=(state.options.zoom-1)*Math.max(state.view.w,state.view.h)*.42;
        state.pan=[Math.max(-limit,Math.min(limit,d.px+dx)),Math.max(-limit,Math.min(limit,d.py+dy))];
        queue();
      }
    });
    canvas.addEventListener('pointerup', event=>{
      const d=state.drag;
      state.drag=null;
      if(!d || d.moved || !state.view || !state.data || !state.options.onPick)return;
      const rect=canvas.getBoundingClientRect(),{s,tx,ty}=state.view;
      const cell=state.data.byCell.get(slot(Math.floor((event.clientX-rect.left-tx)/s/400),Math.floor((ty-event.clientY+rect.top)/s/400)));
      const changes=state.options.changes;
      state.options.onPick(cell?{...cell,change:changes?(changes[cell.grid_id]||'neither'):(cell.candidate?'baseline':'neither')}:null);
    });
    canvas.addEventListener('pointercancel',()=>{state.drag=null;});
    contexts.set(canvas,state);
    return state;
  }
  function render(canvas,state) {
    const w=canvas.clientWidth,h=canvas.clientHeight;
    if(!w || !h || !state.data) return;
    const ratio=Math.min(window.devicePixelRatio||1,2), ctx=canvas.getContext('2d');
    if(canvas.width!==Math.round(w*ratio) || canvas.height!==Math.round(h*ratio)){
      canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);
    }
    ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,w,h);
    const opt=state.options, d=state.data;
    const layers={areas:true,routes:true,network:true,grids:true,...opt.layers};
    const z=Math.min(8,Math.max(.75,+opt.zoom||1));
    const wide=w/h>2.45;
    const spanX=wide?57900:55500,spanY=wide?30200:33100;
    const s=Math.min(w/spanX,h/spanY)*z;
    if(z<=1)state.pan=[0,0];
    const tx=w*.5-29750*s+state.pan[0],ty=h*.50+34500*s+state.pan[1];
    state.view={s,tx,ty,w,h};
    const aura=ctx.createRadialGradient(w*.53,h*.49,0,w*.52,h*.55,w*.58);
    aura.addColorStop(0,'#1b2135');aura.addColorStop(.56,'#0e1723');aura.addColorStop(1,'#080d14');
    ctx.fillStyle=aura;ctx.fillRect(0,0,w,h);
    ctx.save();ctx.transform(s,0,0,-s,tx,ty);
    // Area/subzone fabric, detailed from official URA polygons and water bodies.
    const shades=['#1e293a','#202b3a','#252d40','#202c3b','#23293c','#1d2c37'];
    for (const [i,path] of d.areaShapes.entries()) {
      ctx.fillStyle=shades[i%shades.length];ctx.fill(path,'evenodd');
      ctx.strokeStyle=layers.areas?state.colors.areas:'rgba(137,157,181,.25)';
      ctx.lineWidth=.65/s;ctx.stroke(path);
    }
    if(layers.areas) {
      ctx.strokeStyle='rgba(119,146,170,.38)';ctx.lineWidth=.42/s;ctx.stroke(d.zoneShape);
    }
    ctx.fillStyle='#152f31';ctx.fill(d.coverShapes[1],'evenodd');
    ctx.fillStyle='#101d29';ctx.fill(d.coverShapes[0],'evenodd');
    ctx.fillStyle='rgba(172,184,219,.52)';
    for(let i=0;i<d.buildings.length;i+=2)ctx.fillRect(d.buildings[i],d.buildings[i+1],Math.max(28,.95/s),Math.max(24,.72/s));
    if(layers.grids) {
      for(const g of d.byCell.values()) {
        ctx.fillStyle=state.colors.grids;ctx.globalAlpha=.05+.030*g.demand;
        ctx.fillRect(g.col*400+18,g.row*400+18,364,364);
      }
    }
    ctx.globalAlpha=1;
    if(layers.routes) {
      ctx.save();
      ctx.strokeStyle = state.colors.routes;
      ctx.lineJoin = 'round';
      ctx.shadowColor = state.colors.routes;
      ctx.shadowBlur = 4 * ratio;
      ctx.globalAlpha = .38;
      ctx.lineWidth = 2.2 / s;
      ctx.stroke(d.busRouteShape);
      ctx.shadowBlur = 0;
      ctx.globalAlpha = .95;
      ctx.lineWidth = .85 / s;
      ctx.stroke(d.busRouteShape);
      ctx.restore();
    }
    if(layers.network) {
      const radius = Math.min(1.6, .65 + .15 * z) / s;
      ctx.fillStyle = state.colors.network;
      ctx.beginPath();
      for (const [x,y] of d.stops) {
        ctx.moveTo(x + radius,y);
        ctx.arc(x,y,radius,0,Math.PI*2);
      }
      ctx.lineWidth = .5 / s;
      ctx.strokeStyle = 'rgba(12,16,20,.65)';
      ctx.stroke();
      ctx.fill();
    }
    if(layers.grids) {
      for(const g of d.byCell.values()){
        const type=opt.changes?(opt.changes[g.grid_id]||'neither'):(g.candidate?'baseline':'neither');
        if(type==='neither')continue;
        const color=state.colors[type];
        if(!color)continue;
        ctx.globalAlpha=.22;ctx.fillStyle=color;ctx.fillRect(g.col*400-45,g.row*400-45,490,490);
        ctx.globalAlpha=type==='retained'?.74:.94;ctx.fillRect(g.col*400+14,g.row*400+14,372,372);
        ctx.globalAlpha=1;
      }
    }
    ctx.restore();
    // Survey lines at real 2 km intervals. Fine and major lines share the local CRS.
    const dx=2000*s;ctx.beginPath();
    for(let x=(tx%dx+dx)%dx;x<w;x+=dx){ctx.moveTo(x,0);ctx.lineTo(x,h);}
    for(let y=(ty%dx+dx)%dx;y<h;y+=dx){ctx.moveTo(0,y);ctx.lineTo(w,y);}
    ctx.strokeStyle='rgba(143,169,192,.10)';ctx.lineWidth=.6;ctx.stroke();
    const used=[];
    ctx.font=(w<480?'8px':'10px')+' "IBM Plex Mono", Consolas, monospace';ctx.textAlign='center';ctx.textBaseline='middle';
    for(const name of labelAreas) {
      const label=name==='DOWNTOWN CORE'?'DOWNTOWN':name, [x,y]=d.labels[name];
      const px=tx+x*s,py=ty-y*s-10;
      const labelWidth=ctx.measureText(label).width;
      const v=[px-labelWidth/2-3,py-7,px+labelWidth/2+3,py+7];
      if(v[0]<3 || v[2]>w-3 || v[1]<12 || v[3]>h-12 || used.some(b=>b[0]<v[2]&&b[2]>v[0]&&b[1]<v[3]&&b[3]>v[1]))continue;
      used.push(v);ctx.lineWidth=2.5;ctx.strokeStyle='#121822';ctx.strokeText(label,px,py);
      ctx.fillStyle='rgba(230,237,247,.87)';ctx.fillText(label,px,py);
    }
  }
  window.drawAtlas=async function(canvas,options={}) {
    const state=contexts.get(canvas)||initialize(canvas);
    state.options=options;
    if(!loading)loading=fetch(asset).then(res=>{if(!res.ok)throw new Error('地图数据加载失败');return res.json()}).then(prepare).catch(err=>{loading=null;throw err});
    state.data=await loading; render(canvas,state);
  };
})();
