/* Read-only nl80211 GET_WIPHY query for the selected wlan0 PHY. */
#include <errno.h>
#include <linux/genetlink.h>
#include <linux/netlink.h>
#include <linux/nl80211.h>
#include <net/if.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#define CAP 65536
static unsigned char buf[CAP];
static int seen[200],eligible[200],malformed;
static int valid(const struct nlattr *a,int left){return left>=4&&a->nla_len>=4&&a->nla_len<=left;}
static unsigned typ(const struct nlattr*a){return a->nla_type&NLA_TYPE_MASK;}
static uint32_t u32(const struct nlattr*a){uint32_t v=0;if(a->nla_len>=8)memcpy(&v,(char*)a+4,4);return v;}
static void frequencies(const struct nlattr*outer){
 int left=outer->nla_len-4;const struct nlattr*entry=(const void*)((const char*)outer+4);
 for(;valid(entry,left);left-=NLA_ALIGN(entry->nla_len),entry=(const void*)((const char*)entry+NLA_ALIGN(entry->nla_len))){
  unsigned mhz=0;int blocked=0,n=entry->nla_len-4;const struct nlattr*a=(const void*)((const char*)entry+4);
  for(;valid(a,n);n-=NLA_ALIGN(a->nla_len),a=(const void*)((const char*)a+NLA_ALIGN(a->nla_len))){
   if(typ(a)==NL80211_FREQUENCY_ATTR_FREQ)mhz=u32(a);
   if(typ(a)==NL80211_FREQUENCY_ATTR_DISABLED||typ(a)==NL80211_FREQUENCY_ATTR_NO_IR||typ(a)==NL80211_FREQUENCY_ATTR_RADAR||typ(a)==NL80211_FREQUENCY_ATTR_NO_20MHZ)blocked=1;
  }
  if(n!=0)malformed=1;
  int ch=0;if(mhz>=2412&&mhz<=2472&&(mhz-2407)%5==0)ch=(mhz-2407)/5;
  else if(mhz>=5180&&mhz<=5825&&(mhz-5000)%5==0)ch=(mhz-5000)/5;
  if(ch>0&&ch<200){seen[ch]=1;if(!blocked)eligible[ch]=1;}
 }
 if(left!=0)malformed=1;
}
static void bands(const struct nlattr*outer){
 int n=outer->nla_len-4;const struct nlattr*b=(const void*)((const char*)outer+4);
 for(;valid(b,n);n-=NLA_ALIGN(b->nla_len),b=(const void*)((const char*)b+NLA_ALIGN(b->nla_len))){
  int m=b->nla_len-4;const struct nlattr*a=(const void*)((const char*)b+4);
  for(;valid(a,m);m-=NLA_ALIGN(a->nla_len),a=(const void*)((const char*)a+NLA_ALIGN(a->nla_len)))if(typ(a)==NL80211_BAND_ATTR_FREQS)frequencies(a);
  if(m!=0)malformed=1;
 }
 if(n!=0)malformed=1;
}
static int sendreq(int fd,int family,int cmd,unsigned flags,int attr,const void*data,int size){
 unsigned char request[256]={0};struct nlmsghdr*h=(void*)request;struct genlmsghdr*g=(void*)(h+1);
 h->nlmsg_len=NLMSG_LENGTH(GENL_HDRLEN);h->nlmsg_type=family;h->nlmsg_flags=NLM_F_REQUEST|flags;h->nlmsg_seq=1;g->cmd=cmd;g->version=1;
 struct nlattr*a=(void*)(request+h->nlmsg_len);a->nla_type=attr;a->nla_len=4+size;memcpy((char*)a+4,data,size);h->nlmsg_len+=NLA_ALIGN(a->nla_len);
 struct sockaddr_nl peer={.nl_family=AF_NETLINK};return sendto(fd,request,h->nlmsg_len,0,(void*)&peer,sizeof(peer));
}
int main(int argc,char **argv){
 int requested=0;
 if(argc!=1){
  if(argc!=3||strcmp(argv[1],"--check-channel"))return 2;
  char *end=NULL;long value=strtol(argv[2],&end,10);
  if(!argv[2][0]||*end||value<1||value>=200)return 2;
  requested=(int)value;
 }
 unsigned index=if_nametoindex("wlan0");if(!index){fputs("wlan0 absent\n",stderr);return 2;}
 int fd=socket(AF_NETLINK,SOCK_RAW,NETLINK_GENERIC);if(fd<0)return 2;
 struct timeval timeout={.tv_sec=4};setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
 struct sockaddr_nl local={.nl_family=AF_NETLINK};if(bind(fd,(void*)&local,sizeof(local)))return 2;
 const char name[]="nl80211";if(sendreq(fd,GENL_ID_CTRL,CTRL_CMD_GETFAMILY,0,CTRL_ATTR_FAMILY_NAME,name,sizeof(name))<0)return 2;
 int bytes=recv(fd,buf,sizeof(buf),MSG_TRUNC),family=0;if(bytes<0||bytes>(int)sizeof(buf))return 2;
 for(struct nlmsghdr*h=(void*)buf;NLMSG_OK(h,bytes);h=NLMSG_NEXT(h,bytes)){
  if(h->nlmsg_type==NLMSG_ERROR||h->nlmsg_len<NLMSG_LENGTH(GENL_HDRLEN))return 2;
  int n=h->nlmsg_len-NLMSG_LENGTH(GENL_HDRLEN);struct nlattr*a=(void*)((char*)NLMSG_DATA(h)+GENL_HDRLEN);
  for(;valid(a,n);n-=NLA_ALIGN(a->nla_len),a=(void*)((char*)a+NLA_ALIGN(a->nla_len)))if(typ(a)==CTRL_ATTR_FAMILY_ID&&a->nla_len>=6){uint16_t v;memcpy(&v,(char*)a+4,2);family=v;}
  if(n!=0)return 2;
 }
 if(bytes!=0)return 2;
 if(!family||sendreq(fd,family,NL80211_CMD_GET_WIPHY,0,NL80211_ATTR_IFINDEX,&index,sizeof(index))<0)return 2;
 bytes=recv(fd,buf,sizeof(buf),MSG_TRUNC);if(bytes<0||bytes>(int)sizeof(buf))return 2;int got=0;
 for(struct nlmsghdr*h=(void*)buf;NLMSG_OK(h,bytes);h=NLMSG_NEXT(h,bytes)){
  if(h->nlmsg_type==NLMSG_ERROR||h->nlmsg_flags&(NLM_F_DUMP_INTR))return 2;
  if(h->nlmsg_type!=family||h->nlmsg_len<NLMSG_LENGTH(GENL_HDRLEN))continue;
  int n=h->nlmsg_len-NLMSG_LENGTH(GENL_HDRLEN);struct nlattr*a=(void*)((char*)NLMSG_DATA(h)+GENL_HDRLEN);
  for(;valid(a,n);n-=NLA_ALIGN(a->nla_len),a=(void*)((char*)a+NLA_ALIGN(a->nla_len)))if(typ(a)==NL80211_ATTR_WIPHY_BANDS){bands(a);got=1;}
  if(n!=0)malformed=1;
 }
 close(fd);if(!got||malformed||bytes!=0)return 2;
 if(requested)return seen[requested]&&eligible[requested]?0:3;
 printf("{\"source\":\"nl80211_get_wiphy\",\"interface\":\"wlan0\",\"channels\":[");int comma=0;
 for(int i=1;i<200;i++)if(seen[i]&&eligible[i]){printf("%s%d",comma?",":"",i);comma=1;}
 puts("]}");return 0;
}
