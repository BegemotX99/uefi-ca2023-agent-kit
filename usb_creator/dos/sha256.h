/* SHA-256 streaming implementation, original project code, MIT license. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
typedef struct { uint32_t h[8],lo,hi; unsigned used; unsigned char block[64]; } SHA256;
static const uint32_t K256[64]={
0x428a2f98UL,0x71374491UL,0xb5c0fbcfUL,0xe9b5dba5UL,0x3956c25bUL,0x59f111f1UL,0x923f82a4UL,0xab1c5ed5UL,
0xd807aa98UL,0x12835b01UL,0x243185beUL,0x550c7dc3UL,0x72be5d74UL,0x80deb1feUL,0x9bdc06a7UL,0xc19bf174UL,
0xe49b69c1UL,0xefbe4786UL,0x0fc19dc6UL,0x240ca1ccUL,0x2de92c6fUL,0x4a7484aaUL,0x5cb0a9dcUL,0x76f988daUL,
0x983e5152UL,0xa831c66dUL,0xb00327c8UL,0xbf597fc7UL,0xc6e00bf3UL,0xd5a79147UL,0x06ca6351UL,0x14292967UL,
0x27b70a85UL,0x2e1b2138UL,0x4d2c6dfcUL,0x53380d13UL,0x650a7354UL,0x766a0abbUL,0x81c2c92eUL,0x92722c85UL,
0xa2bfe8a1UL,0xa81a664bUL,0xc24b8b70UL,0xc76c51a3UL,0xd192e819UL,0xd6990624UL,0xf40e3585UL,0x106aa070UL,
0x19a4c116UL,0x1e376c08UL,0x2748774cUL,0x34b0bcb5UL,0x391c0cb3UL,0x4ed8aa4aUL,0x5b9cca4fUL,0x682e6ff3UL,
0x748f82eeUL,0x78a5636fUL,0x84c87814UL,0x8cc70208UL,0x90befffaUL,0xa4506cebUL,0xbef9a3f7UL,0xc67178f2UL};
#if defined(__WATCOMC__)
/* The intrinsic emits a 32-bit rotate even in our real-mode 16-bit build. */
#define RR(x,n) _lrotr((unsigned long)(x),(n))
#else
#define RR(x,n) (((x)>>(n))|((x)<<(32-(n))))
#endif
static void sha_block(SHA256 *s) {
 uint32_t w[64],a,b,c,d,e,f,g,h,t1,t2,x,y; unsigned i;
 for(i=0;i<16;i++)w[i]=((uint32_t)s->block[i*4]<<24)|((uint32_t)s->block[i*4+1]<<16)|((uint32_t)s->block[i*4+2]<<8)|s->block[i*4+3];
 for(i=16;i<64;i++){x=w[i-15];y=w[i-2];w[i]=w[i-16]+(RR(x,7)^RR(x,18)^(x>>3))+w[i-7]+(RR(y,17)^RR(y,19)^(y>>10));}
 a=s->h[0];b=s->h[1];c=s->h[2];d=s->h[3];e=s->h[4];f=s->h[5];g=s->h[6];h=s->h[7];
 for(i=0;i<64;i++){t1=h+(RR(e,6)^RR(e,11)^RR(e,25))+((e&f)^((~e)&g))+K256[i]+w[i];t2=(RR(a,2)^RR(a,13)^RR(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;}
 s->h[0]+=a;s->h[1]+=b;s->h[2]+=c;s->h[3]+=d;s->h[4]+=e;s->h[5]+=f;s->h[6]+=g;s->h[7]+=h;
}
static void sha_init(SHA256 *s){static const uint32_t init[8]={0x6a09e667UL,0xbb67ae85UL,0x3c6ef372UL,0xa54ff53aUL,0x510e527fUL,0x9b05688cUL,0x1f83d9abUL,0x5be0cd19UL};memcpy(s->h,init,sizeof(init));s->lo=s->hi=s->used=0;}
static void sha_update(SHA256 *s,const unsigned char *p,unsigned n){unsigned take;uint32_t old=s->lo;s->lo+=(uint32_t)n*8;if(s->lo<old)s->hi++;while(n){take=64-s->used;if(take>n)take=n;memcpy(s->block+s->used,p,take);s->used+=take;p+=take;n-=take;if(s->used==64){sha_block(s);s->used=0;}}}
static void sha_final(SHA256 *s,char out[65]){unsigned i;uint32_t lo=s->lo,hi=s->hi;s->block[s->used++]=0x80;if(s->used>56){while(s->used<64)s->block[s->used++]=0;sha_block(s);s->used=0;}while(s->used<56)s->block[s->used++]=0;for(i=0;i<4;i++){s->block[56+i]=(unsigned char)(hi>>(24-i*8));s->block[60+i]=(unsigned char)(lo>>(24-i*8));}sha_block(s);for(i=0;i<8;i++)sprintf(out+i*8,"%08lx",(unsigned long)s->h[i]);out[64]=0;}
static int file_hash(const char *name,char out[65],unsigned long *length){FILE *fp;SHA256 s;unsigned char buffer[4096];size_t n;*length=0;fp=fopen(name,"rb");if(!fp)return 0;sha_init(&s);while((n=fread(buffer,1,sizeof(buffer),fp))!=0){sha_update(&s,buffer,(unsigned)n);*length+=(unsigned long)n;}if(ferror(fp)){fclose(fp);return 0;}fclose(fp);sha_final(&s,out);return 1;}
