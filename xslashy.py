#!/usr/bin/python
# X/Y by Foone, June 27th 2010


import pygame
from pygame.constants import *
import random
WHITE=0
BLACK=1
BOSSBLACK=2
BOSSWHITE=3
COLORS={
	WHITE:(255,255,255),
	BLACK:(0,0,0),
	BOSSBLACK:(100,100,100),
	BOSSWHITE:(200,200,200)
}
OTHERCOLORS={BLACK:COLORS[WHITE],WHITE:COLORS[BLACK]}
SWAPCOLOR={WHITE:BLACK,BLACK:WHITE}
BACKGROUND=(148,206,227)
RUMBLETIME=100

BOSS_TEMPLATE=[
	(BOSSBLACK,1,1),
	(BOSSWHITE,1,0),
	(BOSSWHITE,0,1),
	(BOSSWHITE,2,1),
	(BOSSWHITE,1,2)
]

BULLETBUFFER=100

class QuitEvent(Exception): pass
class RestartEvent(Exception): pass

class GameObject(object):
	def __init__(self,pos,size=(1,1)):
		self.pos=list(pos)
		self.vel=[0.0,0.0]
		self.size=size
	
	def draw(self,screen):
		pass
	
	def canMove(self,pos):
		return True

	def update(self,diff):
		vx,vy=self.vel
		pos=self.pos
		nx=pos[0]+vx*diff
		ny=pos[1]+vy*diff
		if self.canMove((nx,ny)):
			pos[0]=nx
			pos[1]=ny
		else:
			for onx,ony in ((pos[0],ny),(nx,pos[1])):
				if self.canMove((onx,ony)):
					pos[0]=onx
					pos[1]=ony
					return

	def rect(self,pos=None):
		if pos is None:
			pos=self.pos
		x,y=pos
		w,h=self.size
		return pygame.Rect(x,y,w,h)

	def hit(self,obj):
		pass
	
class Speck(GameObject):
	SIZE=32
	SLIDESPEED=200
	def __init__(self,pos,color,screen_size,size=SIZE):
		GameObject.__init__(self,pos,(size,size))
		self.vel=[-Speck.SLIDESPEED,0]
		self.screenWidth=screen_size[0]
		self.color=color
		self.damage=5
	
	def draw(self,screen):
		x,y=self.pos
		w,h=self.size
		screen.fill(COLORS[self.color],(x+2,y+2,w-4,h-4))

class SpeckBullet(Speck):
	SHOTSPEED=400
	SIZE=24
	def __init__(self,pos,color,screen_size,player=False):
		Speck.__init__(self,(pos[0]+4,pos[1]+4),color,screen_size,size=SpeckBullet.SIZE)
		self.vel=[(+1 if player else -1)*SpeckBullet.SHOTSPEED,0.0]
		self.player=player
		self.damage=10

class Player(GameObject):
	SPEED=300.
	SLOWSPEED=150.
	BUFFER=25
	HEALTHCOLOR=(94,174,76)
	MAXHEALTH=100
	SHOTDELAY=0.300
	WINSPEED=400
		
	def __init__(self,game,screensize):
		GameObject.__init__(self,(50,50),(16,16))
		self.keys={K_UP:False,K_DOWN:False,K_LEFT:False,K_RIGHT:False,K_LSHIFT:False,K_LCTRL:False}
		b=Player.BUFFER
		self.safeArea=pygame.Rect(b,b,screensize[0]-b*2,screensize[1]-b*2)
		self.mode=WHITE
		self.screenWidth=screensize[0]
		self.health=Player.MAXHEALTH/2
		self.game=game
		self.shotAccumulator=0.0
		self.winning=False

	def draw(self,screen):
		x,y=self.pos
		w,h=self.size
		if self.health>0:
			screen.fill(OTHERCOLORS[self.mode],(x,y,w,h))
			screen.fill(COLORS[self.mode],(x+2,y+2,w-4,h-4))
	
	def handleKey(self,key,down):
		keys,vel=self.keys,self.vel
		if self.winning:
			return 
		if key in keys:
			keys[key]=down
			speed=Player.SLOWSPEED if keys[K_LSHIFT] else Player.SPEED
			vel[0]=(keys[K_RIGHT]-keys[K_LEFT])*speed
			vel[1]=(keys[K_DOWN]-keys[K_UP])*speed
		else:
			if down:
				if key==K_q:
					self.mode=WHITE
				elif key==K_w:
					self.mode=BLACK
		
	def canMove(self,pos):
		return self.winning or self.safeArea.contains(self.rect(pos))

	def hit(self,obj):
		health=self.health
		if health<=0 or self.winning: # already dead or already won 
			return False
		if obj.color!=self.mode:
			health-=obj.damage
			self.game.startRumble()
			if health<=0:
				self.die()
		else:
			health=min(Player.MAXHEALTH,health+obj.damage)
		self.health=health
		return True
	
	def drawHealth(self,screen):
		w=self.screenWidth
		health=self.health
		if health>0:
			barWidth=health/100.0*w
			screen.fill(Player.HEALTHCOLOR,(w/2-barWidth/2,0,barWidth,16))
		else:
			pass #TODO: draw some kind of game over?

	def die(self):
		self.game.lost()
		pass

	def update(self,diff):
		GameObject.update(self,diff)
		self.shotAccumulator+=diff
		if self.health>0 and self.keys[K_LCTRL] and self.shotAccumulator>Player.SHOTDELAY:
			x,y=self.pos
			self.game.bullets.append(SpeckBullet((x-8,y-8), self.mode, self.game.screen.get_size(), True))
			self.shotAccumulator=0.0 
			self.health-=3
			if self.health<=0:
				self.die()
	
	def startWinning(self):
		self.winning=True
		self.vel=[Player.WINSPEED,0]
		self.game.bullets=[]
		
class BossEnemy(GameObject):
	FLOATSPEED=150
	UP=1
	DOWN=2
	SHOOTDELAY=.150
	HEALTHCOLOR=(174,96,76)
	MAXHEALTH=100
	def __init__(self,pos,screen_size,template,game):
		GameObject.__init__(self,pos)
		sz=Speck.SIZE
		ox,oy=self.pos
		specks=self.specks=[Speck((ox+x*sz,oy+y*sz),color,screen_size) for (color,x,y) in template]
		self.anchor=specks[0]
		self.size=(0,0)
		self.floating=False
		self.changeModePoint=screen_size[0]*0.75
		self.floatDirections=(screen_size[1]*0.15,screen_size[1]*0.85)
		self.shotAccumulator=0.0
		self.game=game
		self.screenSize=screen_size
		self.health=BossEnemy.MAXHEALTH
		
	def draw(self,screen):
		for speck in self.specks:
			speck.draw(screen)
		if self.floating:
			self.drawHealth(screen)
			
	def update(self,diff):
		specks=self.specks
		floating=self.floating
		for speck in specks:
			speck.update(diff)
		self.shotAccumulator+=diff
		x,y=self.anchor.pos
		if floating:
			if floating==BossEnemy.UP and y<self.floatDirections[0]:
				self.setAllVels(yvel=BossEnemy.FLOATSPEED)
				self.floating=BossEnemy.DOWN
			elif floating==BossEnemy.DOWN and y>self.floatDirections[1]:
				self.setAllVels(yvel=-BossEnemy.FLOATSPEED)
				self.floating=BossEnemy.UP
			if self.shotAccumulator>BossEnemy.SHOOTDELAY:
				if random.randint(0,3)==1:
					game=self.game
					self.game.objects.append(SpeckBullet((x,y),SWAPCOLOR[game.player.mode],game.screen.get_size()))
				self.shotAccumulator=0.0
		else:
			if x<self.changeModePoint:
				self.floating=BossEnemy.UP
				self.setAllVels(yvel=-BossEnemy.FLOATSPEED)
	
	def setAllVels(self,xvel=0.0,yvel=0.0):
		for speck in self.specks:
			speck.vel=[xvel,yvel]
	
	def rect(self,pos=None):
		specks=self.specks
		return specks[0].rect().unionall(specks[1:])

	# copy paste code yeah!
	def drawHealth(self,screen):
		w,h=self.screenSize
		health=self.health
		if health>0:
			barWidth=health/100.0*w
			screen.fill(BossEnemy.HEALTHCOLOR,(w/2-barWidth/2,h-16,barWidth,16))

	def hit(self,obj):
		self.health-=5
		if self.health<=0:
			self.game.player.startWinning()
			try:
				self.game.objects.remove(self)
			except ValueError:
				pass
		

class GameJam02(object):
	def __init__(self,title,screen_size):
		pygame.init()
		pygame.display.set_caption(title)
		screen=self.screen=pygame.display.set_mode(screen_size)
		self.altscreen=pygame.Surface(screen_size,0,screen)
		self.rumble=None
		self.player=Player(self,screen_size)
		self.lastUpdate=pygame.time.get_ticks()
		self.loadLevel('level.txt',screen_size)
		self.objects.append(BossEnemy(self.bossPosition,screen_size,BOSS_TEMPLATE,self))
		self.bullets=[]
		self.messageMode=False
		
	def playMessage(self,filename):
		self.loadLevel(filename,self.screen.get_size())
		self.messageMode=True
	
	def loadLevel(self,filename,screen_size):
		objs=[]
		chars={'#':WHITE,'%':BLACK}
		with open(filename,'r') as f:
			for y,line in enumerate(f):
				for x,c in enumerate(line):
					pos=(screen_size[0]+x*Speck.SIZE,(y+1)*Speck.SIZE)
					if c in chars:
						objs.append(Speck(pos,chars[c],screen_size))
					elif c=='*':
						self.bossPosition=pos
		self.objects=objs
	
	def draw(self):
		screen=self.screen
		if self.messageMode:
			screen.fill(BACKGROUND)
			for obj in self.objects:
				obj.draw(screen)
			pygame.display.flip()
			return

		rumble=self.rumble
		player=self.player
		if rumble is not None:
			screen=self.altscreen
		screen.fill(BACKGROUND)
		
		for obj in [player]+self.objects+self.bullets:
			obj.draw(screen)
		
		player.drawHealth(screen)
		if rumble is not None:
			x,y=random.randint(-5,5),random.randint(-5,5)
			self.screen.blit(screen,(x,y))

		pygame.display.flip()
	
	def update(self):
		now=pygame.time.get_ticks()
		diff=(now-self.lastUpdate)/1000.
		player=self.player
		dead=[]
		for obj in [player]+self.objects:
			obj.update(diff)
			if obj is not player and obj.rect().colliderect(player):
				try:
					if player.hit(obj):
						dead.append(obj)
				except AttributeError:
					pass
		for obj in dead:
			try:
				self.objects.remove(obj)
			except ValueError:
				pass
		deadbullet=[]
		for bullet in self.bullets:
			bullet.update(diff)
			for obj in self.objects:
				if obj is not player and obj.rect().colliderect(bullet.rect()):
					deadbullet.append(bullet)
					obj.hit(bullet)
			if not -BULLETBUFFER<bullet.pos[0]<self.screen.get_width()+BULLETBUFFER:
				deadbullet.append(bullet)
		
		for bullet in deadbullet:
			try:
				self.bullets.remove(bullet)
			except ValueError:
				pass
		if self.rumble is not None:
			if now-self.rumble>RUMBLETIME:
				self.rumble=None
		if player.winning and player.pos[0]>self.screen.get_width()*2 and not self.messageMode:
			self.playMessage('winmsg.txt')
		self.lastUpdate=now
	
	def run(self):
		try:
			self.loop()
		except QuitEvent:
			self.shutdown()

	def loop(self):
		player=self.player
		while True:
			self.update()
			self.draw()
			for event in pygame.event.get():
				if event.type==QUIT:
					raise QuitEvent()
				elif event.type==KEYUP:
					if event.key==K_ESCAPE:
						raise QuitEvent()
					elif event.key==K_F2:
						raise RestartEvent()
					elif event.key==K_F10:
						self.playMessage('winmsg.txt')
					player.handleKey(event.key,False)
					
				elif event.type==KEYDOWN:
					player.handleKey(event.key,True)
	
	def lost(self):
		self.playMessage('losemsg.txt')
	
	def shutdown(self):
		pygame.display.quit()
		print "Exiting, but pygame screws up on some OSes. Sorry for the delay..."
	
	def startRumble(self):
		self.rumble=pygame.time.get_ticks()
if __name__=='__main__':
	while True:
		try:
			GameJam02("X/Y",(640,640)).run()
			break
		except RestartEvent:
			pass
			
