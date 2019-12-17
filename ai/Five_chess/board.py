#!/usr/bin/env python
# coding: utf-8

from score import scores as s
from score import players as P
from evaluate_point import scorePoint 
from collections import deque
from zobrist import z
import config

def matrix(size:int) -> list:
    return [[0 for i in range(size)] for j in range(size)]

def fixScore(Type) -> int:  # prevent b
    if s.blocked_four <= Type < s.four:
        if s.blocked_four <= Type < (s.blocked_four + s.three): return s.three
        elif (s.blocked_four + s.three) <= Type < s.blocked_four*2: return s.four
        else: return s.four*2
    return Type

def starTO (point: tuple, points: list) -> bool:
    if not (points and len(points)): return False
    a = point
    for i in range(len(points)):
        b = points[i]
        if abs(a[0]-b[0]) > 4 and abs(a[1]-b[1]) > 4: return False
        if not (a[0] == b[0]) or a[1] == b[1] or abs(a[0]-b[0]) == abs(a[1]-b[1]): return False
    return True

class playersScore:        # new class
    def __init__(self, i=0, j=0) -> dict:
        self.pos = [i,j]
        self.score = 0
    def __lt__(self, other):
        return abs(self.score) < abs(other.score)    # used in vcx.py (result.sort())
        
class Board:
    def __init__(self, size: int) -> None:
        self.evaluateCache = {}
        self.currentSteps = []
        self.allSteps = []   # all chess pieces put by both sides
        self.stepsTail = []
        self._last = [False,False]
        self.count = 0
        self.z = z
        if len(size):       # accept only integer, not lists
            self.board = matrix(size)
            self.size = size 
            self.comScore = matrix(size)
            self.humScore = matrix(size)
            self.scoreCache = [ \
                [],   # placeholder
                [matrix(size) for i in range(4)],  # for player 1 
                [matrix(size) for j in range(4)]]  # for player 2  
        self.initScore()

    def __str__(self):
        if self.size >= 0:
            string = ''
            for i in range(self.size):
                string += ', '.join(self.board[i]) + '\n'
            return string

    def hasNeighbor(self, x: int, y: int, distance: int, count: int) -> bool: # in line 481
        for i in range(x-distance, x+distance + 1):
            if i < 0 or i > self.size: continue
            for j in range( y-distance, y+distance + 1):
                if j < 0 or j > self.size: continue
                elif i == x and j == y : continue
                elif self.board != P.empty:
                    count -= 1
                    if count <= 0 : return True
        return False

     # score for a certain loc for a certain player
    def initScore(self) -> None:  
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i][j] == P.empty:
                    if self.hasNeighbor(i, j, 2, 2):
                        self.comScore[i][j] = scorePoint(self, i, j, P.com)
                        self.humScore[i][j] = scorePoint(self, i, j ,P.hum)
                elif self.board[i][j] == P.com:
                    self.comScore[i][j] = scorePoint(self, i ,j, P.com)
                    self.humScore[i][j] = 0
                elif self.board[i][j] == P.hum:
                    self.humScore[i][j] = scorePoint(self, i ,j, P.hum)
                    self.comScore[i][j] = 0

    def updateScore(self, place: tuple) -> None:     # p => place
        radius = 4
        def update(x, y, direction):
            player = self.board[x][y]
            if player != P.com:
                cs = scorePoint(self, x, y, P.com, direction)
                self.comScore[x][y] = cs
                #statistics
            else: self.comScore[x][y] = 0
            if player != P.hum:
                hs = scorePoint(self, x, y, P.hum, direction)
                self.humScore[x][y] += hs
                #statistics
            else: self.humScore[x][y] = 0
        pass # optimization(optional)
        for i in range(-radius, radius+1):
            if place[1] + i < 0: continue
            if place[1] + i >= self.size : break
            update(place[0] + i, place[1] + i, 0)
        for i in range(-radius, radius+1):
            if place[0] + i < 0: continue
            if place[0] + i >= self.size: break
            update(place[0] + i, place[1] + i, 1)
        for i in range(-radius, radius+1):
            if place[0] + i < 0 or place[1] + i < 0: continue
            if place[0] + i >= self.size or place[1] + 1 >= self.size: break
            update(place[0] + i, place[1] + i, 2)
        for i in range(-radius, radius+1):
            if place[0] + i < 0 or place [1] - i < 0: continue
            if place[0] + i >= self.size or place[1] - i >= self.size: break # or continue?
            update(place[0] + i, place[1] + i, 3)

    
    def put(self, place: tuple, player: int) -> None:
        place.player = player
        print(f'put[{place}] {player}')  # debug
        self.board[place[0]][place[1]] = player
        pass # zobrist.py
        self.updateScore(place)
        self.allSteps.append(place)
        self.currentSteps.append(place)
        self.stepsTail = []  # ??
        self.count += 1

    def remove(self, p):
        #r = self.board[p[0]][p[1]]
        # zobrist & debug
        self.board[p[0]][p[1]] = P.empty
        self.updateScore(p)
        self.allSteps.pop()
        self.currentSteps.pop()
        self.count -= 1

    # omit backward
    def forward(self):
        if len(self.stepsTail) < 2: return
        for i in range(2):
            s = self.stepsTail.pop()
            self.put(s, s.player)
            self.i = i

    def evaluate(self, player: int) -> int:  # current total scores
        self.comMaxScore, self.humMaxScore = 0, 0
        for i in range(self.size):
            for j in range(self.size):  # board[i]??
                if self.board[i][j] == P.com:
                    self.comMaxScore += fixScore(self.comScore[i][j])
                elif self.board[i][j] == P.hum:
                    self.humMaxScore += fixScore(self.humScore[i][j])
        return (1 if player == P.com else -1)*(self.comMaxScore - self.humMaxScore)

    def generator(self, player: int, onlyThrees, starSpread) -> list:
        fives = []
        com_fours = []; hum_fours = []
        com_blockedfours = []; hum_blockedfours = []
        com_doublethrees = []; hum_doublethrees = []
        com_threes = []; hum_threes = []
        com_twos = deque(); hum_twos = deque()
        neighbors = []
        if self.count <= 0: return [7,7]
        attackPoints = []
        defendPoints = []
        if starSpread and config.star: # config.py
            i = len(self.currentSteps) - 1
            while i >= 0:
                place = self.currentSteps[i]
                if (P.reverse(player) == P.com and place.scoreCom >= s.three) \
                    or (P.reverse(player) == P.hum and place.scoreHum >= s.three):
                    defendPoints.append(place); break
                i -= 2 # ??
            j = len(self.currentSteps) - 2
            while j >= 0:
                place = self.currentSteps[i]
                if (player == P.com and place.scoreCom >= s.three) \
                    or (player == P.hum and place.scoreHum >= s.three):
                    attackPoints.append(place); break
                j -= 2 # ??
            if not len(attackPoints): 
                attackPoints.append(self.currentSteps[0] if self.currentSteps[0].player == player else self.currentSteps[1])
            if not len(defendPoints):
                defendPoints.append(self.currentSteps[0] if self.currentSteps[0].player == P.reverse(player) else self.currentSteps[1])
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i][j] == P.empty:
                    if len(self.allSteps) < 6:
                        if not self.hasNeighbor(i, j, 1, 1): continue
                    elif not self.hasNeighbor(i, j, 2, 2): continue
                    
                    place = playersScore(i, j)    # replace p of place
                    place.scoreHum = self.humScore[i][j]
                    place.scoreCom = self.comScore[i][j]
                    place.score = max(place.scoreCom, place.scoreHum)
                    if onlyThrees and place.score < s.three: continue
                    place.player = player
                    pass # starspread
                    if place.scoreCom >= s.five: fives.append(place['pos'])
                    elif place.scoreHum >= s.five: fives.append(place['pos'])
                    elif place.scoreCom >= s.four: com_fours.append(place['pos'])
                    elif place.scoreHum >= s.four: hum_fours.append(place['pos'])
                    elif place.scoreCom >= s.blocked_four: com_blockedfours.append(place['pos'])
                    elif place.scoreHum >= s.blocked_four: hum_blockedfours.append(place['pos'])
                    elif place.scoreCom >= 2*s.three: com_doublethrees.append(place['pos'])
                    elif place.scoreHum >= 2*s.three: hum_doublethrees.append(place['pos'])
                    elif place.scoreCom >= s.three: com_threes.append(place['pos'])
                    elif place.scoreHum >= s.three: hum_threes.append(place['pos'])
                    elif place.scoreCom >= s.two: com_twos.appendleft(place['pos'])
                    elif place.scoreHum >= s.two: hum_twos.appendleft(place['pos'])
                    else: neighbors.append(place)

        if len(fives): return fives
        elif player == P.com and len(com_fours): return com_fours
        elif player == P.hum and len(hum_fours): return hum_fours
        elif player == P.com and len(hum_fours) and len(com_blockedfours): return hum_fours
        elif player == P.hum and len(com_fours) and len(hum_blockedfours): return com_fours
        
        fours = com_fours + hum_fours if player == P.com else hum_fours + com_fours
        blockedfours = com_blockedfours + hum_blockedfours if player == P.hum else hum_blockedfours + com_blockedfours
        if len(fours): return fours + blockedfours

        if player == P.com:
            result:list = com_doublethrees + hum_doublethrees + com_blockedfours + hum_blockedfours + com_threes + hum_threes
        elif player == P.hum: 
            result:list = hum_doublethrees + com_doublethrees + hum_blockedfours + com_blockedfours + hum_threes + com_threes           
        if len(com_doublethrees) or len(hum_doublethrees): return result
        elif onlyThrees: return result

        twos = com_twos + hum_twos if player == P.com else hum_twos + com_twos
        result.append(twos if len(twos) else neighbors)
        if len(result) > config.countLimit: return result[:config.countLimit]
        return result
board = Board(15)