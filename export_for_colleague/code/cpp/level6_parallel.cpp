#include <bits/stdc++.h>
using namespace std;
using U=uint64_t;
const int W=7;
struct Case {int r,h,w,cnt;vector<string> g;};
struct State {array<U,W> bits{}; U hash=0; int pos[3]{},on=0,done=0,covered=0,parent=0,action=0; double score=0;};
struct Link{int parent,action;};
static U mix(U x){x+=0x9e3779b97f4a7c15ULL;x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;x=(x^(x>>27))*0x94d049bb133111ebULL;return x^(x>>31);}
struct Solver {
 Case c; int n,m,words; vector<pair<int,int>> ring,cells; vector<vector<int>> ent; vector<vector<vector<int>>> rays; vector<array<int,3>> configs;
 vector<U> z; array<U,W> full{}; int drow[6]={0,1,1,0,-1,-1},dcol[6]={2,1,-1,-2,-1,1};
 Solver(Case cc):c(cc){
  int r=c.r; n=6*r;
  for(int i=r;i>0;i--)ring.push_back({i,r-i});for(int k=0;k<=r;k++)ring.push_back({0,r+2*k});for(int i=1;i<=r;i++)ring.push_back({i,4*r-(r-i)});for(int i=r+1;i<=2*r;i++)ring.push_back({i,4*r-(i-r)});for(int k=1;k<=r;k++)ring.push_back({2*r,3*r-2*k});for(int i=2*r-1;i>r;i--)ring.push_back({i,i-r});
  vector<vector<int>> idx(c.h,vector<int>(c.w,-1));
  for(int i=0;i<c.h;i++)for(int j=0;j<c.w;j++)if(c.g[i][j]=='M'){idx[i][j]=cells.size();cells.push_back({i,j});}
  m=cells.size();words=(m+63)/64;z.resize(m);for(int i=0;i<m;i++){full[i/64]|=1ULL<<(i%64);z[i]=mix(i+12345);}
  for(int i=0;i<c.h;i++)for(int j=0;j<c.w;j++)if(c.g[i][j]=='O'){for(int d=0;d<6;d++){int a=i+drow[d],b=j+dcol[d];if(a>=0&&a<c.h&&b>=0&&b<c.w&&c.g[a][b]=='M')idx[i][j]=-2;}}
  ent.assign(6,vector<int>(m));rays.assign(6,vector<vector<int>>(n,vector<int>(c.h*c.w,0)));
  for(int d=0;d<6;d++)for(int p=0;p<n;p++){auto [a,b]=ring[p];a+=drow[d];b+=dcol[d];while(a>=0&&a<c.h&&b>=0&&b<c.w&&(c.g[a][b]=='M'||c.g[a][b]=='O')){rays[d][p][a*c.w+b]=1;if(idx[a][b]>=0)ent[d][idx[a][b]]=p;a+=drow[d];b+=dcol[d];}}
  // Store cell identifiers including skirting in the geometry grid.
  ids=idx;
 }
 vector<vector<int>> ids;
 int rd(int x,int y){int v=abs(x-y);return min(v,n-v);}
 vector<array<char,6>> search(array<int,3> ds,int width,int limit,int seed){
  vector<int> inter[3]; int paira[3]={0,0,1},pairb[3]={1,2,2};
  vector<array<U,W>> rayBits(n); vector<int> rayForbid(n),rayForbiddenCell(n,-1);
  for(int p=0;p<n;p++)for(int i=0;i<c.h;i++)for(int j=0;j<c.w;j++)if(rays[ds[0]][p][i*c.w+j]){
   int id=ids[i][j];if(id>=0)rayBits[p][id/64]|=1ULL<<(id%64);else if(id==-2){rayForbid[p]++;rayForbiddenCell[p]=-100-i*c.w-j;}
  }
  bool useful=false;for(int p=0;p<n;p++){int cov=0;for(auto x:rayBits[p])cov+=__builtin_popcountll(x);if(cov>=3&&rayForbid[p]<=1)useful=true;}if(!useful)return {};
  for(int q=0;q<3;q++){inter[q].assign(n*n,-1);int a=ds[paira[q]],b=ds[pairb[q]];for(int x=0;x<n;x++)for(int y=0;y<n;y++)for(int i=0;i<c.h;i++)for(int j=0;j<c.w;j++)if(rays[a][x][i*c.w+j]&&rays[b][y][i*c.w+j])inter[q][x*n+y]=q==0?x:(ids[i][j]>=0?ids[i][j]:(ids[i][j]==-2?-100-i*c.w-j:-10000-i*c.w-j));}
  int ns=n*n*n*8;struct Eff{int a,b,c,erase;};vector<Eff> effects(ns,{-3,-3,-3,-3});
  vector<array<unsigned char,4>> moves(n);for(int x=0;x<n;x++)moves[x]={(unsigned char)x,(unsigned char)((x+1)%n),(unsigned char)((x+n-1)%n),(unsigned char)x};
  vector<array<int,3>> cost(m);vector<vector<unsigned char>> dist(3,vector<unsigned char>(n*m));for(int d=0;d<3;d++)for(int p=0;p<n;p++)for(int k=0;k<m;k++)dist[d][p*m+k]=rd(p,ent[ds[d]][k]);
  vector<State> beam(1);for(int d=0;d<3;d++)beam[0].pos[d]=ds[d]*c.r;
  vector<vector<Link>> layers;layers.push_back({{-1,0}});U fullHash=0;for(U v:z)fullHash^=v;
  unordered_map<U,int> seen;seen.reserve(width*limit*2);
  for(int depth=1;depth<=limit;depth++){
   vector<State> next;next.reserve(width*64);unordered_map<U,int> index;index.reserve(width*64);
   for(int pi=0;pi<(int)beam.size();pi++){
    const State &s=beam[pi];
    for(int ac=0;ac<64;ac++){
     State t=s;t.parent=pi;t.action=ac;int a0=ac&3,a1=(ac>>2)&3,a2=(ac>>4)&3;t.pos[0]=moves[s.pos[0]][a0];t.pos[1]=moves[s.pos[1]][a1];t.pos[2]=moves[s.pos[2]][a2];t.on=s.on^((a0==3)|((a1==3)<<1)|((a2==3)<<2));
     int key=((t.pos[0]*n+t.pos[1])*n+t.pos[2])*8+t.on;Eff &e=effects[key];
     if(e.a==-3){
      int v[3];for(int q=0;q<3;q++)v[q]=((t.on&(1<<paira[q]))&&(t.on&(1<<pairb[q])))?inter[q][t.pos[paira[q]]*n+t.pos[pairb[q]]]:-1;
      if(v[0]>=0){
       int er=(t.on&4)?v[1]:-1; int p=v[0];
       e={-1,-1,p,er};
       if(rayForbid[p]-(er==rayForbiddenCell[p]&&rayForbid[p]==1)>0)e.a=-4;
      }else{
       e={v[1],v[2],-1,-1};
       for(int *v:{&e.a,&e.b}){if(*v<=-10000)*v=-1;else if(*v<=-100)*v=-2;}
       if(e.a==-2||e.b==-2)e.a=-4;
      }
     }
     if(e.a==-4)continue;
     if(e.erase>=0){int k=e.erase;U bit=1ULL<<(k%64);if(t.bits[k/64]&bit){t.bits[k/64]^=bit;t.covered--;t.hash^=z[k];}}
     if(e.c>=0)for(int w=0;w<words;w++){
      U add=rayBits[e.c][w]&~t.bits[w];if(e.erase>=0&&e.erase/64==w)add&=~(1ULL<<(e.erase%64));
      t.bits[w]|=add;t.covered+=__builtin_popcountll(add);while(add){int k=__builtin_ctzll(add);t.hash^=z[w*64+k];add&=add-1;}
     }
     for(int k:{e.a,e.b})if(k>=0){U bit=1ULL<<(k%64);if(!(t.bits[k/64]&bit)){t.bits[k/64]|=bit;t.covered++;t.hash^=z[k];}}
     if(t.covered==m){t.done++;t.covered=0;t.bits={};t.hash=0;}
     if(t.done==c.cnt){
      vector<int> acts{ac};int p=pi;for(int dep=depth-1;dep>0;dep--){acts.push_back(layers[dep][p].action);p=layers[dep][p].parent;}reverse(acts.begin(),acts.end());vector<array<char,6>> ans;
      for(int v:acts){array<char,6> row;row.fill('-');for(int d=0;d<3;d++){row[ds[d]]="-FBT"[(v>>(d*2))&3];}ans.push_back(row);}return ans;
     }
     U hk=t.hash^mix(key+U(t.done)*ns);auto old=seen.find(hk);if(old!=seen.end()&&old->second<depth)continue;
     auto it=index.find(hk);if(it!=index.end())continue;
     index[hk]=next.size();next.push_back(t);
    }
   }
   if(next.empty())break;
   // Evaluate coverage and a lower bound on reaching all remaining targets.
   for(State &t:next){
    int nearest=n,far=0,sum=0,uncovered=0;
    for(int k=0;k<m;k++)if(!(t.bits[k/64]>>(k%64)&1)){
     int a=dist[0][t.pos[0]*m+k]+!(t.on&1),b=dist[1][t.pos[1]*m+k]+!(t.on&2),d=dist[2][t.pos[2]*m+k]+!(t.on&4);
     int v=a+b+d-min({a,b,d})-max({a,b,d});nearest=min(nearest,v);far=max(far,v);sum+=v;uncovered++;
    }
    double rem=(c.cnt-t.done)*m-t.covered;
    t.score=rem*(seed>=3?0.55+0.1*(seed%3):1.0+0.1*(seed%3))+nearest*(seed>=3?0.9:0.6)+far*(seed>=3?0.6:0.35)+(uncovered?double(sum)/uncovered*0.2:0)+((mix(t.hash+seed+depth*99)&65535)/65536.0)*0.08;
   }
   if((int)next.size()>width){int pool=min((int)next.size(),width*(seed>=3?8:1));if(pool<(int)next.size())nth_element(next.begin(),next.begin()+pool,next.end(),[](auto&a,auto&b){return a.score<b.score;});next.resize(pool);if(seed>=3){sort(next.begin(),next.end(),[](auto&a,auto&b){return a.score<b.score;});vector<State> chosen;vector<int> rejected;unordered_map<U,int> counts;for(int j=0;j<(int)next.size()&&(int)chosen.size()<width;j++){U key=next[j].hash^mix(next[j].done);if(counts[key]++<8)chosen.push_back(next[j]);else rejected.push_back(j);}for(int j:rejected)if((int)chosen.size()<width)chosen.push_back(next[j]);next=move(chosen);}else next.resize(width);}
   vector<Link> links;links.reserve(next.size());for(auto &s:next){links.push_back({s.parent,s.action});int key=((s.pos[0]*n+s.pos[1])*n+s.pos[2])*8+s.on;seen.emplace(s.hash^mix(key+U(s.done)*ns),depth);}
   layers.push_back(move(links));beam=move(next);
  }
  return {};
 }
};
int main(int argc,char**argv){
 if(argc<3){cerr<<"input output [width=64] [first=0] [last=all] [orientationMask=255] [seed=0]\n";return 1;}
 ifstream f(argv[1]);int N;f>>N;vector<Case> cs(N);for(auto &c:cs){f>>c.r>>c.h>>c.w>>c.cnt;c.g.resize(c.h);for(auto &s:c.g)f>>s;}
 string out=argv[2];filesystem::create_directories(out);int width=argc>3?atoi(argv[3]):64,first=argc>4?atoi(argv[4]):0,last=argc>5?min(N,atoi(argv[5])):N,mask=argc>6?atoi(argv[6]):255,seed=argc>7?atoi(argv[7]):0;
 for(int i=first;i<last;i++){
  Solver sol(cs[i]);vector<array<char,6>> best;string path=out+"/case_"+to_string(i)+".txt";ifstream old(path);string line;while(getline(old,line))if(!line.empty()){istringstream is(line);array<char,6> a;for(char &x:a)is>>x;best.push_back(a);}
  int orig=best.size();for(int cfg=0;cfg<6;cfg++)if(mask&(1<<cfg)){
   int opposite=cfg/2,other=(opposite+1+cfg%2)%3; array<int,3> dirs{opposite,opposite+3,other};int lim=best.empty()?int(sol.m*cs[i].cnt*1.8+cs[i].r*4+30):best.size()-1;
   auto ans=sol.search(dirs,width,lim,seed);if(!ans.empty()&&(best.empty()||ans.size()<best.size()))best=move(ans);
  }
  if(!best.empty()){ofstream o(path);for(auto a:best){for(int d=0;d<6;d++)o<<a[d]<<(d==5?'\n':' ');}}
  cerr<<i<<" m="<<sol.m<<" count="<<cs[i].cnt<<" old="<<orig<<" best="<<best.size()<<endl;
 }
}
