/* Test fixture only. It never accesses SPI. DO NOT package as vendor FPT. */
#include <stdio.h>
#include <string.h>
static int copy(const char *from,const char *to){FILE *a,*b;char buf[8192];unsigned n;a=fopen(from,"rb");if(!a)return 2;b=fopen(to,"wb");if(!b){fclose(a);return 3;}while((n=fread(buf,1,sizeof(buf),a))!=0){if(fwrite(buf,1,n,b)!=n){fclose(a);fclose(b);return 4;}}fclose(a);return fclose(b)?5:0;}
int main(int argc,char **argv){FILE *f;char mode[32]="";int result;if(argc!=3)return 9;f=fopen("MODE.TXT","r");if(f){fgets(mode,sizeof(mode),f);fclose(f);}if(!strncmp(mode,"FAIL",4)){puts("SIMULATED vendor failure 99");return 99;}if(!strcmp(argv[1],"-d"))return copy("CHIP.BIN",argv[2]);if(!strcmp(argv[1],"-f")){result=copy(argv[2],"CHIP.BIN");if(!strncmp(mode,"CORRUPT",7)){f=fopen("CHIP.BIN","r+b");if(f){fputc(0,f);fclose(f);}}puts("SIMULATION write completed");return result;}return 8;}
