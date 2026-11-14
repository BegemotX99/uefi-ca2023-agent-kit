/* Prism full-SPI backup/write menu. Original source, MIT license.
 * FPT is a separately supplied unmodified vendor utility. No unlock/force flags.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <conio.h>
#include <i86.h>
#include <io.h>
#include "sha256.h"
#include "board_data.h"

#define FULL_SIZE 16777216UL
static unsigned short far *video;
static int selected=0;
static const Board *board=0;
static char status_text[160]="Ready. Select a full-chip operation.";
static void palette(int n,int r,int g,int b){outp(0x3c8,n);outp(0x3c9,r);outp(0x3c9,g);outp(0x3c9,b);}
static void put(int x,int y,const char *s,int color){int i=0;while(*s&&x+i<80){video[y*80+x+i]=(unsigned char)*s++|((unsigned short)color<<8);i++;}}
static void cursor(int x,int y){union REGS r;r.h.ah=2;r.h.bh=0;r.h.dh=(unsigned char)y;r.h.dl=(unsigned char)x;int86(0x10,&r,&r);}
static void log_line(const char *s){FILE *f=fopen("FLASH.LOG","a");if(f){fprintf(f,"%s\n",s);fclose(f);}}
static void screen(void){int i;union REGS r;r.h.ah=0;r.h.al=3;int86(0x10,&r,&r);palette(1,3,6,10);palette(3,0,30,34);palette(7,45,52,59);palette(0x38,27,36,44);palette(0x3b,10,55,57);palette(0x3f,59,62,63);video=(unsigned short far *)MK_FP(0xb800,0);for(i=0;i<2000;i++)video[i]=0x1720;
 put(3,1,"PRISM / SPI FLASH",0x1b);put(57,1,"FULL IMAGE 16 MiB",0x1f);
 put(3,3,"PREPARED FOR",0x18);put(3,4,board?board->name:"INVALID BOARD.CFG",0x1f);
 put(3,6,"BIOS.BIN  16,777,216 bytes  |  full descriptor + ME + BIOS",0x17);
 put(3,7,"Prebuilt Secure Boot defaults use the author's key.",0x18);
 put(3,10," 1   BACKUP ENTIRE 16 MiB   - save a new BACKnnnn.BIN",selected==0?0x30:0x17);
 put(3,12," 2   WRITE ENTIRE 16 MiB    - confirm FLASH; read back + compare",selected==1?0x30:0x17);
 put(3,14," 0   EXIT TO DOS",selected==2?0x30:0x17);
 put(3,17,"STATUS / RESULT",0x1b);put(3,18,status_text,0x1f);if(strlen(status_text)>74)put(3,19,status_text+74,0x1f);
 put(3,21,"SPI access locks and unsupported parts stop the operation.",0x18);
 put(3,23,"Arrow keys + Enter   |   1 / 2 / 0   |   Logs: FLASH.LOG, FPT*.LOG",0x17);
 if(PRISM_SIMULATION)put(22,0,"SIMULATION BUILD - FILE-BASED CHIP ONLY",0x4f);
 cursor(0,24);
}
static void set_status(const char *s){strncpy(status_text,s,sizeof(status_text)-1);status_text[sizeof(status_text)-1]=0;log_line(s);screen();}
static void wait_key(void){put(3,20,"Press any key to return to the menu.",0x1b);getch();}
static int new_name(char *out,const char *prefix,const char *ext){unsigned i;FILE *f;for(i=1;i<10000;i++){sprintf(out,"%s%04u.%s",prefix,i,ext);f=fopen(out,"rb");if(!f)return 1;fclose(f);}return 0;}
static int check_tool(void){char hash[65];unsigned long size;if(!file_hash("FPT.EXE",hash,&size)||strcmp(hash,FPT_HASH)){set_status("STOPPED: FPT.EXE identity does not match the bundled vendor tool.");return 0;}if(!file_hash("FPARTS.TXT",hash,&size)||strcmp(hash,PARTS_HASH)){set_status("STOPPED: FPARTS.TXT was changed. No flash operation permitted.");return 0;}return 1;}
static int run_fpt(const char *operation,const char *file,const char *log){char command[140];int code;
 sprintf(command,"FPT.EXE %s %s > %s",operation,file,log);log_line(command);code=system(command);
 {char result[80];sprintf(result,"FPT return status: %d; output: %s",code,log);log_line(result);}
 return code==0;
}
static void show_tool_error(const char *name){FILE *f;char line[160],tail[4][160];int count=0,i,start;screen();for(i=17;i<=22;i++)put(3,i,"                                                                            ",0x17);put(3,16,"FPT STOPPED - last output lines (full details are in the log):",0x4f);f=fopen(name,"r");if(f){while(fgets(line,sizeof(line),f)){line[strcspn(line,"\r\n")]=0;if(*line){strcpy(tail[count%4],line);count++;}}fclose(f);start=count>4?count-4:0;for(i=start;i<count;i++)put(3,18+i-start,tail[i%4],0x1f);}put(3,22,"Press any key to return to the menu.",0x1b);getch();}
static int full_file(const char *name,char hash[65]){unsigned long size;if(!file_hash(name,hash,&size)||size!=FULL_SIZE)return 0;return 1;}
static void backup(void){char name[13],hash[65];FILE *f;
 if(!check_tool()){wait_key();return;}
 if(!new_name(name,"BACK","BIN")){set_status("STOPPED: no unused BACKnnnn.BIN filename remains.");wait_key();return;}
 set_status("Reading all 16 MiB. Wait; FPT output goes to FPTBACK.LOG.");
 if(!run_fpt("-d",name,"FPTBACK.LOG")){set_status("BACKUP FAILED. Any partial file is not a verified backup.");show_tool_error("FPTBACK.LOG");return;}
 if(!full_file(name,hash)){set_status("BACKUP FAILED: full-chip dump must be exactly 16,777,216 bytes.");wait_key();return;}
 f=fopen("BACKUPS.TXT","a");if(f){fprintf(f,"%s  %s  16777216 bytes\n",hash,name);fclose(f);}
 {char result[110];sprintf(result,"BACKUP SAVED: %s, full 16 MiB; SHA-256 in BACKUPS.TXT.",name);set_status(result);}
 log_line(hash);wait_key();
}
static void write_spi(void){char hash[65],readhash[65],probe[13],verify[13],answer[32];int i;
 if(!check_tool()){wait_key();return;}
 set_status("Checking selected BIOS.BIN SHA-256 and exact full-image size...");
 if(!full_file("BIOS.BIN",hash)||strcmp(hash,board->sha256)){set_status("STOPPED: BIOS.BIN is missing, altered or not the selected full 16 MiB image.");wait_key();return;}
 if(!new_name(probe,"PRB","TMP")){set_status("STOPPED: no unused preflight scratch filename.");wait_key();return;}
 set_status("Preflight: read entire SPI to confirm full-chip access and 16 MiB capacity.");
 if(!run_fpt("-d",probe,"FPTPRE.LOG")||!full_file(probe,readhash)){set_status("STOPPED: full 16 MiB SPI preflight read failed. No write attempted.");show_tool_error("FPTPRE.LOG");return;}
 remove(probe);
 log_line("Waiting for typed FLASH confirmation.");
 screen();put(3,17,"WRITE CONFIRMATION - motherboard must match the selected image",0x4f);
 put(3,18,"This writes the entire 16 MiB SPI chip. Keep power connected.",0x1f);
 put(3,19,"Type FLASH and press Enter, or press Enter alone to cancel:",0x1b);
 cursor(3,20);memset(answer,0,sizeof(answer));fgets(answer,sizeof(answer),stdin);
 answer[strcspn(answer,"\r\n")]=0;
 if(strcmp(answer,"FLASH")){set_status("Write cancelled. No firmware write was attempted.");wait_key();return;}
 /* Recheck immediately before invoking the writer. */
 if(!full_file("BIOS.BIN",hash)||strcmp(hash,board->sha256)){set_status("STOPPED: BIOS image changed after preflight.");wait_key();return;}
 set_status("WRITING ENTIRE 16 MiB. Do not interrupt. FPT output: FPTWRITE.LOG.");
 if(!run_fpt("-f","BIOS.BIN","FPTWRITE.LOG")){set_status("WRITE FAILED. Keep power on; preserve logs and record the FPT error.");show_tool_error("FPTWRITE.LOG");return;}
 if(!new_name(verify,"VRF","TMP")){set_status("WRITE returned success, but no readback filename is available. NOT VERIFIED.");wait_key();return;}
 set_status("Reading the entire 16 MiB back and comparing SHA-256. Wait...");
 if(!run_fpt("-d",verify,"FPTVER.LOG")||!full_file(verify,readhash)||strcmp(hash,readhash)){set_status("READBACK VERIFICATION FAILED. Keep power on; preserve image and logs.");show_tool_error("FPTVER.LOG");return;}
 remove(verify);log_line(readhash);
 set_status("SUCCESS: entire 16 MiB SPI readback matches BIOS.BIN exactly.");
 put(3,20,"Shut down manually after recording the result; no automatic reboot.",0x1b);getch();
}
int main(int argc,char **argv){FILE *f;char id[32],hash[65];unsigned long length;unsigned i;int c;
 if(argc==3&&!strcmp(argv[1],"--hash")){if(!file_hash(argv[2],hash,&length))return 1;printf("%s  %s  %lu\n",hash,argv[2],length);return 0;}
 f=fopen("BOARD.CFG","r");if(!f){puts("Missing BOARD.CFG. No flash operation is available.");return 1;}
 if(!fgets(id,sizeof(id),f)){fclose(f);return 1;}fclose(f);id[strcspn(id,"\r\n")]=0;
 for(i=0;i<BOARD_COUNT;i++)if(!strcmp(id,BOARDS[i].id))board=&BOARDS[i];
 if(!board){puts("Unknown BOARD.CFG. No flash operation is available.");return 1;}
 log_line("PRISM menu started; selected board:");log_line(board->name);screen();
 for(;;){c=getch();if(c==0||c==224){c=getch();if(c==72)selected=(selected+2)%3;if(c==80)selected=(selected+1)%3;screen();continue;}
  if(c=='0'||c==27)break;
  if(c=='1'){selected=0;c=13;}if(c=='2'){selected=1;c=13;}
  if(c==13){if(selected==0)backup();else if(selected==1)write_spi();else break;screen();}
 }
 return 0;
}
