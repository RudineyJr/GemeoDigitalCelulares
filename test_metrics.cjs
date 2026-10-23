const assert=require('node:assert/strict');
const {buildMetrics,calculateFunctionalOEE}=require('./metrics.js');
const costs={SPI:15,AOI:60,'Teste funcional':240,unit:240};
const names=['SPI','AOI','Teste funcional','Embalagem'];
const event=(t,p,s,e,r='pendente')=>({t,p,s,e,r});
const events=[
 event(0,'A','SPI','entrada'),event(0,'B','SPI','fila'),
 event(1,'A','SPI','saida','aprovada'),event(1,'A','AOI','entrada'),
 event(1,'B','SPI','saida','reprovada'),event(1,'C','SPI','entrada'),
 event(2,'A','AOI','saida','aprovada'),event(2,'A','Teste funcional','entrada'),
 event(2,'C','SPI','saida','aprovada'),event(2,'C','AOI','entrada'),
 event(3,'A','Teste funcional','saida','aprovada'),event(3,'A','Embalagem','entrada'),
 event(3,'C','AOI','saida','aprovada'),event(3,'C','Teste funcional','entrada'),
 event(4,'A','Embalagem','saida','aprovada'),event(4,'C','Teste funcional','saida','reprovada')];
const engine=buildMetrics(events,names,costs,2),m=engine.at(4);
assert.equal(m.p,1);assert.equal(m.bad,2);assert.equal(m.total,3);assert.equal(m.w,0);
assert.equal(m.q,50);assert.ok(Math.abs(m.r-100/3)<1e-10);
assert.equal(m.target,50);
assert.equal(m.c,255);assert.equal(m.rejects.SPI,1);assert.equal(m.rejects['Teste funcional'],1);
assert.equal(engine.at(0).q,null);assert.equal(engine.at(0).r,null);
assert.ok(Math.abs(m.costScore-(100*(1-255/720)))<1e-10);
const wait=buildMetrics([event(0,'A','SPI','fila'),event(5,'A','SPI','entrada'),event(8,'A','SPI','saida','aprovada')],['SPI'],costs);
assert.equal(wait.at(10).queueMean,0.5);assert.equal(wait.at(10).queueMax,1);assert.equal(wait.at(10).b,0);
const noInspections=buildMetrics([event(0,'A','Teste funcional','entrada'),event(1,'A','Teste funcional','saida','aprovada')],['Teste funcional','Embalagem'],costs);
assert.equal(noInspections.at(1).q,100);assert.equal(noInspections.at(1).r,100);
assert.equal(buildMetrics([],names,costs).at(0).costScore,null);
console.log('Metricas: conservacao, FPY, RTY, custos, COPQ, WIP medio/maximo e ausencia de amostras OK');

assert.equal(m.oee,50);
assert.equal(m.testTotal,2);
assert.equal(m.testGood,1);
assert.equal(m.oeePerformance,100);
assert.equal(m.oeeAvailability,100);
assert.equal(m.oeeQuality,50);
// OEE contabiliza a aprovação no teste antes de concluir a embalagem.
const beforePack=buildMetrics([event(0,'A','Teste funcional','entrada'),event(26,'A','Teste funcional','saida','aprovada'),event(26,'A','Embalagem','entrada')],['Teste funcional','Embalagem'],costs,26).at(26);
assert.equal(beforePack.p,0);
assert.equal(beforePack.testGood,1);
assert.equal(beforePack.oee,100);
assert.equal(calculateFunctionalOEE(0,0,60,26).oee,null);
assert.equal(calculateFunctionalOEE(1,1,0,26).oee,null);
assert.equal(calculateFunctionalOEE(1,1,60,0).oee,null);
for(const [total,good] of [[1050,987],[1049,1047]]){
 const result=calculateFunctionalOEE(good,total,28800,26);
 assert.ok(Math.abs(result.oee-(result.oeeAvailability/100)*(result.oeePerformance/100)*(result.oeeQuality/100)*100)<1e-10);
 assert.ok(Math.abs(result.oee-good*26/28800*100)<1e-10);
}
console.log('OEE do TFF: contagens, ciclo, tempo programado, produto A/P/Q e independencia da embalagem OK');
