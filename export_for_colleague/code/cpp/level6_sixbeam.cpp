#include <bits/stdc++.h>
using namespace std;
using U=uint64_t;
const int W=7;
struct Case {int r,h,w,cnt;vector<string> g;};
struct State {array<U,W> bits{}; U hash=0; int pos[6]{},on=0,done=0,covered=0,parent=0,action=0; double score=0;};
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
 vector<array<char,6>> search(array<int,6> ds,int width,int limit,int seed){
  vector<vector<int>> inter[15]; int paira[15],pairb[15];for(int d=0,q=0;d<6;d++)for(int e=d+1;e<6;e++){paira[q]=d;pairb[q++]=e;}
  for(int q=0;q<15;q++){inter[q].resize(n*n);int a=ds[paira[q]],b=ds[pairb[q]];for(int x=0;x<n;x++)for(int y=0;y<n;y++)for(int i=0;i<c.h;i++)for(int j=0;j<c.w;j++)if(rays[a][x][i*c.w+j]&&rays[b][y][i*c.w+j])inter[q][x*n+y].push_back(i*c.w+j);}
  U ns=U(n)*n*n*n*n*n*64;struct Eff{array<short,128> cells{};unsigned char np=0,ne=0;bool valid=true;};unordered_map<U,Eff> effects;effects.reserve(100000);
  vector<array<unsigned char,4>> moves(n);for(int x=0;x<n;x++)moves[x]={(unsigned char)x,(unsigned char)((x+1)%n),(unsigned char)((x+n-1)%n),(unsigned char)x};
  vector<array<int,4>> cost(m);vector<vector<unsigned char>> dist(6,vector<unsigned char>(n*m));for(int d=0;d<6;d++)for(int p=0;p<n;p++)for(int k=0;k<m;k++)dist[d][p*m+k]=rd(p,ent[ds[d]][k]);
  vector<State> beam(1);for(int d=0;d<6;d++)beam[0].pos[d]=ds[d]*c.r;
  vector<vector<Link>> layers;layers.push_back({{-1,0}});U fullHash=0;for(U v:z)fullHash^=v;
  unordered_map<U,int> seen;seen.reserve(width*limit*2);
  for(int depth=1;depth<=limit;depth++){
   vector<State> next;next.reserve(width*4096);unordered_map<U,int> index;index.reserve(width*4096);
   for(int pi=0;pi<(int)beam.size();pi++){
    const State &s=beam[pi];
    vector<pair<int,int>> nearests;
    for(int k=0;k<m;k++)if(!(s.bits[k/64]>>(k%64)&1)){
      int vv[6];for(int d=0;d<6;d++)vv[d]=dist[d][s.pos[d]*m+k]+!(s.on&(1<<d));nth_element(vv,vv+1,vv+6);nearests.push_back({vv[1],k});
    }
    sort(nearests.begin(),nearests.end());if(nearests.size()>5)nearests.resize(5);
    for(int ac=0;ac<4096;ac++){
     State t=s;t.parent=pi;t.action=ac;for(int d=0;d<6;d++){int a=(ac>>(d*2))&3;t.pos[d]=moves[s.pos[d]][a];if(a==3)t.on^=1<<d;}
     U key=(((((U(t.pos[0])*n+t.pos[1])*n+t.pos[2])*n+t.pos[3])*n+t.pos[4])*n+t.pos[5])*64+t.on;
     // Inactive positions do not change emissions.
     U ek=0;for(int d=0;d<6;d++)ek=ek*(n+1)+((t.on&(1<<d))?t.pos[d]:n);
     auto eit=effects.find(ek);
     if(eit==effects.end()){
      Eff e;int checked[128],nc=0;short paints[128],erases[128];int np=0,ne=0;
      for(int q=0;q<15&&e.valid;q++)if((t.on&(1<<paira[q]))&&(t.on&(1<<pairb[q])))for(int k:inter[q][t.pos[paira[q]]*n+t.pos[pairb[q]]]){
       bool duplicate=false;for(int j=0;j<nc;j++)if(checked[j]==k){duplicate=true;break;}if(duplicate)continue;checked[nc++]=k;
       int count=0;for(int d=0;d<6;d++)if((t.on&(1<<d))&&rays[ds[d]][t.pos[d]][k])count++;
       int id=ids[k/c.w][k%c.w];if(count==2){if(id==-2){e.valid=false;break;}if(id>=0)paints[np++]=id;}else if(count>=3&&id>=0)erases[ne++]=id;
      }
      e.np=np;e.ne=ne;for(int j=0;j<np;j++)e.cells[j]=paints[j];for(int j=0;j<ne;j++)e.cells[np+j]=erases[j];eit=effects.emplace(ek,e).first;
     }
     const Eff &e=eit->second;if(!e.valid)continue;
     for(int j=e.np;j<e.np+e.ne;j++){int k=e.cells[j];U bit=1ULL<<(k%64);if(t.bits[k/64]&bit){t.bits[k/64]^=bit;t.covered--;t.hash^=z[k];}}
     for(int j=0;j<e.np;j++){int k=e.cells[j];U bit=1ULL<<(k%64);if(!(t.bits[k/64]&bit)){t.bits[k/64]|=bit;t.covered++;t.hash^=z[k];}}
     int near=n;for(auto [ignored,k]:nearests)if(!(t.bits[k/64]>>(k%64)&1)){int vv[6];for(int d=0;d<6;d++)vv[d]=dist[d][t.pos[d]*m+k]+!(t.on&(1<<d));nth_element(vv,vv+1,vv+6);near=min(near,vv[1]);}if(near==n)near=0;
     t.score=((c.cnt-t.done)*m-t.covered)*(1.0+0.1*(seed%3))+0.65*near+((mix(t.hash+key+seed+depth*99)&65535)/65536.0)*0.12;
     if(t.covered==m){t.done++;t.covered=0;t.bits={};t.hash=0;}
     if(t.done==c.cnt){
      vector<int> acts{ac};int p=pi;for(int dep=depth-1;dep>0;dep--){acts.push_back(layers[dep][p].action);p=layers[dep][p].parent;}reverse(acts.begin(),acts.end());vector<array<char,6>> ans;
      for(int v:acts){array<char,6> row;row.fill('-');for(int d=0;d<6;d++){row[ds[d]]="-FBT"[(v>>(d*2))&3];}ans.push_back(row);}return ans;
     }
     U hk=t.hash^mix(key+U(t.done)*ns);auto old=seen.find(hk);if(old!=seen.end()&&old->second<depth)continue;
     auto it=index.find(hk);if(it!=index.end())continue;
     index[hk]=next.size();next.push_back(t);
    }
   }
   if(next.empty())break;
   // Retain multiple positions for productive states; near-target progress guides dark moves.
   if((int)next.size()>width){nth_element(next.begin(),next.begin()+width,next.end(),[](auto&a,auto&b){return a.score<b.score;});next.resize(width);}
   vector<Link> links;links.reserve(next.size());for(auto &s:next){links.push_back({s.parent,s.action});U key=(((((U(s.pos[0])*n+s.pos[1])*n+s.pos[2])*n+s.pos[3])*n+s.pos[4])*n+s.pos[5])*64+s.on;seen.emplace(s.hash^mix(key+U(s.done)*ns),depth);}
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
   array<int,6> dirs{cfg,(cfg+1)%6,(cfg+2)%6,(cfg+3)%6,(cfg+4)%6,(cfg+5)%6};int lim=best.empty()?int(sol.m*cs[i].cnt*1.7+cs[i].r*4+40):best.size()-1;
   auto ans=sol.search(dirs,width,lim,seed);if(!ans.empty()&&(best.empty()||ans.size()<best.size()))best=move(ans);
  }
  if(!best.empty()){ofstream o(path);for(auto a:best){for(int d=0;d<6;d++)o<<a[d]<<(d==5?'\n':' ');}}
  cerr<<i<<" m="<<sol.m<<" count="<<cs[i].cnt<<" old="<<orig<<" best="<<best.size()<<endl;
 }
}
