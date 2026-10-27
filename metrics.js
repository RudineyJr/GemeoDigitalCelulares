// OEE do recurso Teste Funcional Final, com um posto de teste.
// Sem eventos de paradas no modelo: disponibilidade assumida em 100%.
function calculateFunctionalOEE(good,total,plannedSeconds,idealCycleSeconds) {
  const validTime=Number.isFinite(plannedSeconds)&&plannedSeconds>0&&Number.isFinite(idealCycleSeconds)&&idealCycleSeconds>0;
  const validCounts=Number.isInteger(good)&&Number.isInteger(total)&&good>=0&&total>=good;
  const measured=validTime&&validCounts&&total>0;
  return {
    oee:measured?100*good*idealCycleSeconds/plannedSeconds:null,
    oeeAvailability:validTime?100:null,
    oeePerformance:validTime&&validCounts?100*total*idealCycleSeconds/plannedSeconds:null,
    oeeQuality:measured?100*good/total:null,
    oeePlannedSeconds:validTime?plannedSeconds:null,
    oeeIdealCycle:validTime?idealCycleSeconds:null,
    oeeTheoreticalCount:validTime?plannedSeconds/idealCycleSeconds:null
  };
}
// OEE simplificado da linha: saída boa na embalagem e referência comum.
// Retenções SPI/AOI não são NG; apenas reprovações finais entram na qualidade.
function calculateLineOEE(good,finalNG,plannedSeconds,idealCycleSeconds=20) {
  const result=calculateFunctionalOEE(good,good+finalNG,plannedSeconds,idealCycleSeconds);
  return {...result,oee:plannedSeconds>0&&Number.isFinite(plannedSeconds)&&Number.isInteger(good)&&good>=0&&Number.isInteger(finalNG)&&finalNG>=0&&Number.isFinite(idealCycleSeconds)&&idealCycleSeconds>0?100*good*idealCycleSeconds/plannedSeconds:null};
}
// Cálculos puros, compartilhados pela interface e pelos testes.
function buildMetrics(events, names, costs, lineIdealCycle=20) {
  const inspections=names.filter(n=>['SPI','AOI','Teste funcional'].includes(n));
  const counts=Object.fromEntries(inspections.map(n=>[n,{total:0,passed:0,rejected:0}]));
  const latest=new Map(), starts=new Map();
  let good=0,bad=0,queue=0,cost=0,lead=0,queueArea=0,queueMax=0,previous=0;
  const series=[];
  for(let i=0;i<events.length;) {
    const t=events[i].t;
    queueArea+=queue*(t-previous); previous=t;
    while(i<events.length && events[i].t===t) {
      const e=events[i++],old=latest.get(e.p);
      if(old?.e==='fila')queue--;
      if(e.e==='fila')queue++;
      latest.set(e.p,e);
      if(!starts.has(e.p))starts.set(e.p,e.t);
      if(e.e==='saida') {
        if(counts[e.s]) {counts[e.s].total++; if(e.r==='reprovada')counts[e.s].rejected++;else counts[e.s].passed++;}
        if(e.r==='reprovada') {bad++;cost+=costs[e.s]??0;}
        if(e.s==='Embalagem') {good++;lead+=t-starts.get(e.p);}
      }
    }
    queueMax=Math.max(queueMax,queue);
    const assessed=inspections.length>0&&inspections.every(n=>counts[n].total>0);
    const rty=assessed?100*inspections.reduce((v,n)=>v*counts[n].passed/counts[n].total,1):null;
    const test=counts['Teste funcional'];
    const fpy=test?.total?100*test.passed/test.total:null;
    series.push({t,p:good,w:starts.size-good-bad,b:queue,c:cost,r:rty,q:fpy,
      testGood:test?.passed??0,testTotal:test?.total??0,testRejected:test?.rejected??0,
      total:starts.size,bad,lead:good?lead/good:0,queueArea,queueMax,
      rejects:Object.fromEntries(inspections.map(n=>[n,counts[n].rejected]))});
  }
  function at(t) {
    let low=0,high=series.length;
    while(low<high){const mid=(low+high)>>1;if(series[mid].t<=t)low=mid+1;else high=mid;}
    const item=low?series[low-1]:{t:0,p:0,w:0,b:0,c:0,r:null,q:null,testGood:0,testTotal:0,testRejected:0,total:0,bad:0,lead:0,queueArea:0,queueMax:0,rejects:{}};
    const reference=item.total*costs.unit;
    const oee=calculateLineOEE(item.p,item.testRejected,t,lineIdealCycle);
    return {...item,...oee,queueMean:t?(item.queueArea+item.b*(t-item.t))/t:0,
      target:oee.oee, // Alias mantido para compatibilidade; interfaces usam oee explicitamente.
      costScore:reference>0?100*(1-item.c/reference):null};
  }
  return {series,at};
}
if(typeof module!=='undefined')module.exports={buildMetrics,calculateFunctionalOEE,calculateLineOEE};
