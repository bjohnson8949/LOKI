#!/usr/bin/env python

import apsw
import datetime
import ftplib
import httplib
import os
import sys
import time
import zlib

from contextlib import contextmanager

import loki_db


class Source():
	
	
	# ##################################################
	# constructor
	
	
	def __init__(self, lokidb):
		assert(isinstance(lokidb, loki_db.Database))
		assert(self.__class__.__name__.startswith('Source_'))
		self._loki = lokidb
		self._db = lokidb._db
		self._sourceID = self.addSource(self.getSourceName())
		assert(self._sourceID > 0)
	#__init__()
	
	
	# ##################################################
	# source interface
	
	
	def download(self):
		raise Exception("invalid LOKI Source plugin: download() not implemented")
	#download()
	
	
	def update(self):
		raise Exception("invalid LOKI Source plugin: update() not implemented")
	#update()
	
	
	# ##################################################
	# context managers
	
	
	def __enter__(self):
		return self._loki.__enter__()
	#__enter__()
	
	
	def __exit__(self, excType, excVal, traceback):
		return self._loki.__exit__(excType, excVal, traceback)
	#__exit__()
	
	
	@contextmanager
	def bulkUpdateContext(self,
			group=False, group_name=False, group_group=False, group_region=False,
			region=False, region_name=False, region_bound=False,
			snp=False, snp_merge=False, snp_role=False
	):
		tableList = []
		if group:
			tableList.append('group')
		if group_name:
			tableList.append('group_name')
		if group_group:
			tableList.append('group_group')
		if group_region:
			tableList.append('group_region_name')
		if region:
			tableList.append('region')
		if region_name:
			tableList.append('region_name')
		if region_bound:
			tableList.append('region_bound')
		if snp:
			tableList.append('snp')
		if snp_merge:
			tableList.append('snp_merge')
		if snp_role:
			tableList.append('snp_role_entrez')
		with self._loki:
			if len(tableList) > 0:
				self._loki.dropDatabaseIndexes(None, 'db', tableList)
			yield
			if len(tableList) > 0:
				self._loki.createDatabaseIndexes(None, 'db', tableList)
			if region_bound:
				self.updateRegionZones()
			if region_name or snp_role:
				self.resolveSNPRoles()
			if region_name or group_region:
				self.resolveGroupRegions()
		#with db transaction
	#bulkUpdateContext()
	
	
	# ##################################################
	# instance management
	
	
	def getSourceName(self):
		return self.__class__.__name__[7:]
	#getSourceName()
	
	
	def getSourceID(self):
		return self._sourceID
	#getSourceID()
	
	
	def log(self, message=""):
		return self._loki.log(message)
	#log()
	
	
	def logPush(self, message=None):
		return self._loki.logPush(message)
	#logPush()
	
	
	def logPop(self, message=None):
		return self._loki.logPop(message)
	#logPop()
	
	
	
	# ##################################################
	# metadata management
	
	
	def addNamespace(self, name, multigene=0):
		result = self._loki.getNamespaceID(name)
		if not result:
			self._db.cursor().execute("INSERT INTO `db`.`namespace` (`namespace`,`multigene`) VALUES (LOWER(?),?)", (name,multigene))
			result = self._db.last_insert_rowid()
		return result
	#addNamespace()
	
	
	def addNamespaces(self, namespaces):
		# namespaces=[ (namespace,multigene), ... ]
		result = self._loki.getNamespaceIDs(n[0] for n in namespaces)
		for n in namespaces:
			if not result[n[0]]:
				self._db.cursor().execute("INSERT INTO `db`.`namespace` (`namespace`,`multigene`) VALUES (LOWER(?),?)", n)
				result[n[0]] = self._db.last_insert_rowid()
		return result
	#addNamespaces()
	
	
	def addPopulation(self, name, comment=None, desc=None):
		result = self._loki.getPopulationID(name)
		if not result:
			self._db.cursor().execute("INSERT INTO `db`.`population` (`population`,`ldcomment`,`description`) VALUES (LOWER(?),?,?)", (name,comment,desc))
			result = self._db.last_insert_rowid()
		return result
	#addPopulation()
	
	
	def addPopulations(self, populations):
		result = self._loki.getPopulationIDs(p[0] for p in populations)
		for p in populations:
			if not result[p[0]]:
				self._db.cursor().execute("INSERT INTO `db`.`population` (`population`,`ldcomment`,`description`) VALUES (LOWER(?),?,?)", p)
				result[p[0]] = self._db.last_insert_rowid()
		return result
	#addPopulations()
	
	
	def addRelationship(self, name):
		result = self._loki.getRelationshipID(name)
		if not result:
			self._db.cursor().execute("INSERT INTO `db`.`relationship` (`relationship`) VALUES (LOWER(?))", (name,))
			result = self._db.last_insert_rowid()
		return result
	#addRelationship()
	
	
	def addRelationships(self, names):
		result = self._loki.getRelationshipIDs(names)
		for name in names:
			if not result[name]:
				self._db.cursor().execute("INSERT INTO `db`.`relationship` (`relationship`) VALUES (LOWER(?))", (name,))
				result[name] = self._db.last_insert_rowid()
		return result
	#addRelationships()
	
	
	def addRole(self, name, desc=None, coding=None, exon=None):
		result = self._loki.getRoleID(name)
		if not result:
			self._db.cursor().execute("INSERT INTO `db`.`role` (`role`,`description`,`coding`,`exon`) VALUES (LOWER(?),?,?,?)", (name,desc,coding,exon))
			result = self._db.last_insert_rowid()
		return result
	#addRole()
	
	
	def addRoles(self, roles):
		result = self._loki.getRoleIDs(r[0] for r in roles)
		for r in roles:
			if not result[r[0]]:
				self._db.cursor().execute("INSERT INTO `db`.`role` (`role`,`description`,`coding`,`exon`) VALUES (LOWER(?),?,?,?)", r)
				result[r[0]] = self._db.last_insert_rowid()
		return result
	#addRoles()
	
	
	def addSource(self, name):
		result = self._loki.getSourceID(name)
		if not result:
			self._db.cursor().execute("INSERT INTO `db`.`source` (`source`) VALUES (LOWER(?))", (name,))
			result = self._db.last_insert_rowid()
		return result
	#addSource()
	
	
	def addSources(self, names):
		result = self._loki.getSourceIDs(names)
		for name in names:
			if not result[name]:
				self._db.cursor().execute("INSERT INTO `db`.`source` (`source`) VALUES (LOWER(?))", (name,))
				result[name] = self._db.last_insert_rowid()
		return result
	#addSources()
	
	
	def addType(self, name):
		result = self._loki.getTypeID(name)
		if not result:
			self._db.cursor().execute("INSERT INTO `db`.`type` (`type`) VALUES (LOWER(?))", (name,))
			result = self._db.last_insert_rowid()
		return result
	#addType()
	
	
	def addTypes(self, names):
		result = self._loki.getTypeIDs(names)
		for name in names:
			if not result[name]:
				self._db.cursor().execute("INSERT INTO `db`.`type` (`type`) VALUES (LOWER(?))", (name,))
				result[name] = self._db.last_insert_rowid()
		return result
	#addTypes()
	
	
	# ##################################################
	# data management
	
	
	def deleteSourceData(self):
		dbc = self._db.cursor()
		dbc.execute("DELETE FROM `db`.`group` WHERE `source_id` = ?", (self._sourceID,))
		dbc.execute("DELETE FROM `db`.`group_name` WHERE `source_id` = ?", (self._sourceID,))
		dbc.execute("DELETE FROM `db`.`group_group` WHERE `source_id` = ?", (self._sourceID,))
		dbc.execute("DELETE FROM `db`.`group_region_name` WHERE `source_id` = ?", (self._sourceID,))
		dbc.execute("DELETE FROM `db`.`region` WHERE `source_id` = ?", (self._sourceID,))
		dbc.execute("DELETE FROM `db`.`region_name` WHERE `source_id` = ?", (self._sourceID,))
		dbc.execute("DELETE FROM `db`.`region_bound` WHERE `source_id` = ?", (self._sourceID,))
		dbc.execute("DELETE FROM `db`.`snp` WHERE `source_id` = ?", (self._sourceID,))
		dbc.execute("DELETE FROM `db`.`snp_merge` WHERE `source_id` = ?", (self._sourceID,))
		dbc.execute("DELETE FROM `db`.`snp_role_entrez` WHERE `source_id` = ?", (self._sourceID,))
	#deleteSourceData()
	
	
	def addGroups(self, groupList):
		# groupList=[ (type_id,label,description), ... ]
		retList = []
		for row in self._db.cursor().executemany(
				"INSERT INTO `db`.`group` (`type_id`,`label`,`description`,`source_id`) VALUES (?,?,?,?); SELECT last_insert_rowid()",
				((g[0],g[1],g[2],self._sourceID) for g in groupList)
		):
			retList.append(row[0])
		return retList
	#addGroups()
	
	
	def addTypedGroups(self, typeID, groupList):
		# groupList=[ (label,description), ... ]
		retList = []
		for row in self._db.cursor().executemany(
				"INSERT INTO `db`.`group` (`type_id`,`label`,`description`,`source_id`) VALUES (?,?,?,?); SELECT last_insert_rowid()",
				((typeID,g[0],g[1],self._sourceID) for g in groupList)
		):
			retList.append(row[0])
		return retList
	#addTypedGroups()
	
	
	def addGroupNames(self, nameList):
		# nameList=[ (group_id,namespace_id,name), ... ]
		self._db.cursor().executemany(
				"INSERT OR IGNORE INTO `db`.`group_name` (`group_id`,`namespace_id`,`name`,`source_id`) VALUES (?,?,?,?)",
				((n[0],n[1],n[2],self._sourceID) for n in nameList)
		)
	#addGroupNames()
	
	
	def addNamespacedGroupNames(self, namespaceID, nameList):
		# nameList=[ (group_id,name), ... ]
		self._db.cursor().executemany(
				"INSERT OR IGNORE INTO `db`.`group_name` (`group_id`,`namespace_id`,`name`,`source_id`) VALUES (?,?,?,?)",
				((n[0],namespaceID,n[1],self._sourceID) for n in nameList)
		)
	#addNamespacedGroupNames()
	
	
	def addGroupGroups(self, linkList):
		# linkList=[ (group_id,related_group_id,relationship_id), ... ]
		self._db.cursor().executemany(
				"INSERT OR IGNORE INTO `db`.`group_group` (`group_id`,`related_group_id`,`relationship_id`,`direction`,`source_id`) VALUES (?,?,?,?,?)",
				((l[0],l[1],l[2],1,self._sourceID) for l in linkList)
		)
		self._db.cursor().executemany(
				"INSERT OR IGNORE INTO `db`.`group_group` (`group_id`,`related_group_id`,`relationship_id`,`direction`,`source_id`) VALUES (?,?,?,?,?)",
				((l[1],l[0],l[2],-1,self._sourceID) for l in linkList)
		)
	#addGroupGroups()
	
	
	#def addGroupRegions(self, linkList):
	#	# linkList=[ (group_id,region_id), ... ]
	#	self._db.cursor().executemany(
	#			"INSERT OR IGNORE INTO `db`.`group_region` (`group_id`,`region_id`,`source_id`) VALUES (?,?,?)",
	#			((link[0],link[1],self._sourceID) for link in linkList)
	#	)
	#addGroupRegions()
	
	
	def addGroupRegionNames(self, regionList):
		# regionList=[ (group_id,member,namespace_id,name), ... ]
		self._db.cursor().executemany(
				"INSERT OR IGNORE INTO `db`.`group_region_name` (`group_id`,`member`,`namespace_id`,`name`,`source_id`) VALUES (?,?,?,?,?)",
				((r[0],r[1],r[2],r[3],self._sourceID) for r in regionList)
		)
	#addGroupRegionNames()
	
	
	def addNamespacedGroupRegionNames(self, namespaceID, regionList):
		# regionList=[ (group_id,member,name), ... ]
		self._db.cursor().executemany(
				"INSERT OR IGNORE INTO `db`.`group_region_name` (`group_id`,`member`,`namespace_id`,`name`,`source_id`) VALUES (?,?,?,?,?)",
				((r[0],r[1],namespaceID,r[2],self._sourceID) for r in regionList)
		)
	#addNamespacedGroupRegionNames()
	
	
	def resolveGroupRegions(self):
		dbc = self._db.cursor()
		# calculate scores for each possible name match
		dbc.execute("""
CREATE TEMP TABLE `temp`.`group_region_name_score` (
  group_id INTERGER NOT NULL,
  member INTEGER NOT NULL,
  region_id INTEGER NOT NULL,
  multigene TINYINT NOT NULL,
  implication INTEGER NOT NULL,
  quality INTEGER NOT NULL,
  PRIMARY KEY (group_id, member, region_id)
)
""")
		dbc.execute("""
INSERT INTO `temp`.`group_region_name_score`
SELECT
  group_id,
  member,
  region_id,
  MAX(multigene) AS multigene,
  COUNT(DISTINCT rn.namespace_id||'.'||rn.name) AS implication,
  SUM(1000 / region_count) AS quality
FROM (
  SELECT
    group_id,
    member,
    namespace_id,
    name,
    COUNT(DISTINCT region_id) AS region_count
  FROM `db`.`group_region_name`
  JOIN `db`.`region_name` USING (namespace_id, name)
  GROUP BY group_id, member, namespace_id, name
)
JOIN `db`.`region_name` AS `rn` USING (namespace_id, name)
JOIN `db`.`namespace` AS `n` USING (namespace_id)
GROUP BY group_id, member, region_id
""")
		# generate group_region assignments with confidence scores
		self._loki.dropDatabaseIndexes(None, 'db', 'group_region')
		dbc.execute("DELETE FROM `db`.`group_region`")
		dbc.execute("""
INSERT INTO `db`.`group_region`
SELECT
  group_id,
  region_id,
  MAX(specificity) AS specificity,
  MAX(implication) AS implication,
  MAX(quality) AS quality
FROM (
  /* identify specific matches with the best score for each member */
  SELECT
    group_id,
    member,
    region_id,
    (CASE
      WHEN multigene = 1 THEN 100
      WHEN member_multigene = 1 THEN 1
      ELSE 100 / count_basic
    END) AS specificity,
    (CASE
      WHEN multigene = 1 THEN 100
      WHEN member_multigene = 1 THEN 1
      WHEN implication = member_implication THEN 100 / count_implication
      ELSE 0
    END) AS implication,
    (CASE
      WHEN multigene = 1 THEN 100
      WHEN member_multigene = 1 THEN 1
      WHEN quality = member_quality THEN 100 / count_quality
      ELSE 0
    END) AS quality
  FROM (
    /* identify number of matches with the best score for each member */
    SELECT
      group_id,
      member,
      member_multigene,
      COUNT(DISTINCT region_id) AS count_basic,
      member_implication,
      SUM(CASE WHEN implication = member_implication THEN 1 ELSE 0 END) AS count_implication,
      member_quality,
      SUM(CASE WHEN quality = member_quality THEN 1 ELSE 0 END) AS count_quality
    FROM (
      /* identify best scores for each member */
      SELECT
        group_id,
        member,
        MAX(multigene) AS member_multigene,
        MAX(implication) AS member_implication,
        MAX(quality) AS member_quality
      FROM `temp`.`group_region_name_score`
      GROUP BY group_id, member
    )
    JOIN `temp`.`group_region_name_score` USING (group_id, member)
    GROUP BY group_id, member
  )
  JOIN `temp`.`group_region_name_score` USING (group_id, member)
  GROUP BY group_id, member, region_id
)
GROUP BY group_id, region_id
""")
		# generate group_region placeholders for unrecognized members
		dbc.execute("""
INSERT OR IGNORE INTO `db`.`group_region`
SELECT
  group_id,
  0 AS region_id,
  100*COUNT() AS specificity,
  100*COUNT() AS implication,
  100*COUNT() AS quality
FROM (
  SELECT group_id
  FROM `db`.`group_region_name`
  LEFT JOIN `db`.`region_name` USING (namespace_id, name)
  GROUP BY group_id, member
  HAVING MAX(region_id) IS NULL
)
GROUP BY group_id
""")
		dbc.execute("DROP TABLE `temp`.`group_region_name_score`")
		self._loki.createDatabaseIndexes(None, 'db', 'group_region')
	#resolveGroupRegions()
	
	
	def addRegions(self, regionList):
		# regionList=[ (type_id,label,description), ... ]
		retList = []
		for row in self._db.cursor().executemany(
				"INSERT INTO `db`.`region` (`type_id`,`label`,`description`,`source_id`) VALUES (?,?,?,?); SELECT last_insert_rowid()",
				((r[0],r[1],r[2],self._sourceID) for r in regionList)
		):
			retList.append(row[0])
		return retList
	#addRegions()
	
	
	def addTypedRegions(self, typeID, regionList):
		# regionList=[ (label,description), ... ]
		retList = []
		for row in self._db.cursor().executemany(
				"INSERT INTO `db`.`region` (`type_id`,`label`,`description`,`source_id`) VALUES (?,?,?,?); SELECT last_insert_rowid()",
				((typeID,r[0],r[1],self._sourceID) for r in regionList)
		):
			retList.append(row[0])
		return retList
	#addTypedRegions()
	
	
	def addRegionNames(self, nameList):
		# nameList=[ (region_id,namespace_id,name), ... ]
		self._db.cursor().executemany(
				"INSERT OR IGNORE INTO `db`.`region_name` (`region_id`,`namespace_id`,`name`,`source_id`) VALUES (?,?,?,?)",
				((n[0],n[1],n[2],self._sourceID) for n in nameList)
		)
	#addRegionNames()
	
	
	def addNamespacedRegionNames(self, namespaceID, nameList):
		# nameList=[ (region_id,name), ... ]
		self._db.cursor().executemany(
				"INSERT OR IGNORE INTO `db`.`region_name` (`region_id`,`namespace_id`,`name`,`source_id`) VALUES (?,?,?,?)",
				((n[0],namespaceID,n[1],self._sourceID) for n in nameList)
		)
	#addNamespacedRegionNames()
	
	
	def addRegionBounds(self, boundList):
		# boundList=[ (region_id,population_id,chr,posMin,posMax), ... ]
		self._db.cursor().executemany(
				"INSERT OR IGNORE INTO `db`.`region_bound` (`region_id`,`population_id`,`chr`,`posMin`,`posMax`,`source_id`) VALUES (?,?,?,?,?,?)",
				((b[0],b[1],b[2],min(b[3],b[4]),max(b[3],b[4]),self._sourceID) for b in boundList)
		)
	#addRegionBounds()
	
	
	def addPopulationRegionBounds(self, populationID, boundList):
		# boundList=[ (region_id,chr,posMin,posMax), ... ]
		self._db.cursor().executemany(
				"INSERT OR IGNORE INTO `db`.`region_bound` (`region_id`,`population_id`,`chr`,`posMin`,`posMax`,`source_id`) VALUES (?,?,?,?,?,?)",
				((b[0],populationID,b[1],min(b[2],b[3]),max(b[2],b[3]),self._sourceID) for b in boundList)
		)
	#addPopulationRegionBounds()
	
	
	def updateRegionZones(self):
		dbc = self._db.cursor()
		for row in dbc.execute("SELECT MAX(`posMax`) FROM `db`.`region_bound`"):
			maxZone = int(row[0]) / 100000
		dbc.execute("CREATE TEMP TABLE `temp`.`zones` (`zone` INTEGER PRIMARY KEY NOT NULL)")
		dbc.executemany("INSERT INTO `temp`.`zones` (`zone`) VALUES (?)", ((zone,) for zone in xrange(maxZone+1)))
		self._loki.dropDatabaseIndexes(None, 'db', 'region_zone')
		dbc.execute("DELETE FROM `db`.`region_zone`")
		dbc.execute("""
INSERT OR IGNORE INTO `db`.`region_zone` (`region_id`,`population_id`,`chr`,`zone`)
SELECT rb.`region_id`, rb.`population_id`, rb.`chr`, tz.`zone`
FROM `db`.`region_bound` AS rb
JOIN `temp`.`zones` AS tz
  ON tz.`zone` >= rb.`posMin` / ?
  AND tz.`zone` <= rb.`posMax` / ?
""", (100000,100000))
		dbc.execute("DROP TABLE `temp`.`zones`")
		self._loki.createDatabaseIndexes(None, 'db', 'region_zone')
	#updateRegionZones()
	
	
	def addSNPs(self, snpList):
		# snpList=[ (rs,chr,pos), ... ]
		self._db.cursor().executemany(
				"INSERT INTO `db`.`snp` (`rs`,`chr`,`pos`,`source_id`) VALUES (?,?,?,?)",
				((s[0],s[1],s[2],self._sourceID) for s in snpList)
		)
	#addChromosomeSNPs()
	
	
	def addChromosomeSNPs(self, chromosome, snpList):
		# snpList=[ (rs,pos), ... ]
		self._db.cursor().executemany(
				"INSERT INTO `db`.`snp` (`rs`,`chr`,`pos`,`source_id`) VALUES (?,?,?,?)",
				((s[0],chromosome,s[1],self._sourceID) for s in snpList)
		)
	#addChromosomeSNPs()
	
	
	def addSNPMerges(self, mergeList):
		# mergeList=[ (rsOld,rsNew,rsCur), ... ]
		self._db.cursor().executemany(
				"INSERT INTO `db`.`snp_merge` (`rsOld`,`rsNew`,`rsCur`,`source_id`) VALUES (?,?,?,?)",
				((m[0],m[1],m[2],self._sourceID) for m in mergeList)
		)
	#addSNPMerges()
	
	
	def addEntrezSNPRoles(self, roleList):
		# roleList=[ (rs,entrez,role_id), ... ]
		self._db.cursor().executemany(
				"INSERT OR IGNORE INTO `db`.`snp_role_entrez` (`rs`,`region_entrez`,`role_id`,`source_id`) VALUES (?,?,?,?)",
				((r[0],r[1],r[2],self._sourceID) for r in roleList)
		)
	#addEntrezSNPRoles()
	
	
	def resolveSNPRoles(self):
		dbc = self._db.cursor()
		self._loki.dropDatabaseIndexes(None, 'db', 'snp_role')
		dbc.execute("DELETE FROM `db`.`snp_role`")
		dbc.execute("""
INSERT OR IGNORE INTO `db`.`snp_role`
SELECT rsr.rs, rn.region_id, rsr.role_id
FROM `db`.`snp_role_entrez` AS rsr
JOIN `db`.`region_name` AS rn
  ON rn.namespace_id = ? AND rn.name = rsr.region_entrez
""", (self.addNamespace('entrez_id'),))
		self._loki.createDatabaseIndexes(None, 'db', 'snp_role')
	#resolveSNPRoles()
	
	
	# ##################################################
	# source utility methods
	
	
	def zfile(self, fileName, splitChar="\n", chunkSize=1*1024*1024):
		dc = zlib.decompressobj(zlib.MAX_WBITS | 32) # autodetect gzip or zlib header
		with open(fileName,'rb') as filePtr:
			text = ""
			loop = True
			while loop:
				data = filePtr.read(chunkSize)
				if data:
					text += dc.decompress(data)
					data = None
				else:
					text += dc.flush()
					loop = False
				if text:
					lines = text.split(splitChar)
					i,x = 0,len(lines)-1
					text = lines[x]
					while i < x:
						yield lines[i]
						i += 1
					lines = None
			#while data remains
			if text:
				yield text
		#with fileName
	#zfile()
	
	
	# unlike split(), delim must be specified and only the first character of will be considered
	def split_escape(self, string, delim, escape=None, limit=0, reverse=False):
		tokens = []
		current = ""
		escaping = False
		
		# parse string
		for char in string:
			if escaping:
				current += char
				escaping = False
			elif (escape) and (char == escape):
				escaping = True
			elif char == delim[0]:
				tokens.append(current)
				current = ""
			else:
				current += char
		if current != "":
			tokens.append(current)
		
		# re-merge the splits that exceed the limit
		if (limit > 0) and (len(tokens) > (limit + 1)):
			if reverse:
				tokens[0:-limit] = [ delim[0].join(tokens[0:-limit]) ]
			else:
				tokens[limit:] = [ delim[0].join(tokens[limit:]) ]
		
		return tokens
	#split_escape()
	
	
	def rsplit_escape(self, string, delim, escape=None, limit=0):
		return self.split_escape(string, delim, escape, limit, True)
	#rsplit_escape()
	
	
	def findConnectedComponents(self, neighbors):
		f = set()
		c = list()
		for v in neighbors:
			if v not in f:
				f.add(v)
				c.append(self._findConnectedComponents_recurse(neighbors, v, f, {v}))
		return c
	#findConnectedComponents()
	
	
	def _findConnectedComponents_recurse(self, n, v, f, c):
		for u in n[v]:
			if u not in f:
				f.add(u)
				c.add(u)
				self._findConnectedComponents_recurse(n, v, f, c)
		return c
	#_findConnectedComponents_recurse()
	
	
	def findEdgeDisjointCliques(self, neighbors):
		# neighbors = {'a':{'b','c'}, 'b':{'a'}, 'c':{'a'}, ...}
		# 'a' not in neighbors['a']
		# 'b' in neighbors['a'] => 'a' in neighbors['b']
		
		# clone neighbors so we can modify the local copy
		n = { v:set(neighbors[v]) for v in neighbors }
		c = list()
		
		while True:
			# prune isolated vertices and extract hanging pairs
			for v in n.keys():
				try:
					if len(n[v]) == 0:
						del n[v]
					elif len(n[v]) == 1:
						u, = n[v]
						n[v].add(v)
						c.append(n[v])
						del n[v]
						n[u].remove(v)
						if len(n[u]) == 0:
							del n[u]
				except KeyError:
					pass
			#foreach vertex
			
			# if nothing remains, we're done
			if len(n) == 0:
				return c
			
			# find maximal cliques on the remaining graph
			cliques = self.findMaximalCliques(n)
			
			# add disjoint cliques to the solution and remove the covered edges from the graph
			cliques.sort(key=len, reverse=True)
			for clique in cliques:
				ok = True
				for v in clique:
					if len(n[v] & clique) != len(clique) - 1:
						ok = False
						break
				if ok:
					c.append(clique)
					for v in clique:
						n[v] -= clique
			#foreach clique
		#loop
	#findEdgeDisjointCliques()
	
	
	def findMaximalCliques(self, neighbors):
		# neighbors = {'a':{'b','c'}, 'b':{'a'}, 'c':{'a'}, ...}
		# 'a' not in neighbors['a']
		# 'b' in neighbors['a'] => 'a' in neighbors['b']
		#
		# this implementation of the Bron-Kerbosch algorithm incorporates the
		# top-level degeneracy ordering described in:
		#   Listing All Maximal Cliques in Sparse Graphs in Near-optimal Time
		#   David Eppstein, Maarten Loeffler, Darren Strash
		
		# build vertex-degree and degree-vertices maps
		vd = dict()
		dv = list()
		for v in neighbors:
			d = len(neighbors[v])
			vd[v] = d
			while len(dv) <= d:
				dv.append(set())
			dv[d].add(v)
		#foreach vertex
		
		# compute degeneracy ordering
		o = list()
		while len(dv) > 0:
			for dvSet in dv:
				try:
					v = dvSet.pop()
				except KeyError:
					continue
				o.append(v)
				vd[v] = None
				for u in neighbors[v]:
					if vd[u]:
						dv[vd[u]].remove(u)
						vd[u] -= 1
						dv[vd[u]].add(u)
				while len(dv) > 0 and len(dv[-1]) == 0:
					dv.pop()
				break
			#for dvSet in dv (until dvSet is non-empty)
		#while dv remains
		vd = dv = None
		
		# run first recursion layer in degeneracy order
		p = set(o)
		x = set()
		c = list()
		for v in o:
			self._findMaximalCliques_recurse({v}, p & neighbors[v], x & neighbors[v], neighbors, c)
			p.remove(v)
			x.add(v)
		return c
	#findMaximalCliques()
	
	
	def _findMaximalCliques_recurse(self, r, p, x, n, c):
		if len(p) == 0:
			if len(x) == 0:
				return c.append(r)
		else:
			# cursory tests yield best performance by choosing the pivot
			# arbitrarily from x first if x is not empty, else p; also tried
			# picking from p always, picking the pivot with highest degree,
			# and picking the pivot earliest in degeneracy order
			u = iter(x).next() if (len(x) > 0) else iter(p).next()
			for v in (p - n[u]):
				self._findMaximalCliques_recurse(r | {v}, p & n[v], x & n[v], n, c)
				p.remove(v)
				x.add(v)
	#_findMaximalCliques_recurse()
	
	
	# remFiles={'filename.ext':'/path/on/remote/host/to/filename.ext',...}
	def downloadFilesFromFTP(self, remHost, remFiles):
		# check local file sizes and times, and identify all needed remote paths
		remDirs = set()
		remSize = {}
		remTime = {}
		locSize = {}
		locTime = {}
		for locPath in remFiles:
			remDirs.add(remFiles[locPath][0:remFiles[locPath].rfind('/')])
			remSize[locPath] = None
			remTime[locPath] = None
			locSize[locPath] = None
			locTime[locPath] = None
			if os.path.exists(locPath):
				stat = os.stat(locPath)
				locSize[locPath] = long(stat.st_size)
				locTime[locPath] = datetime.datetime.fromtimestamp(stat.st_mtime)
		
		# define FTP directory list parser
		now = datetime.datetime.now()
		def ftpDirCB(line):
			words = line.split()
			if len(words) >= 9 and words[8] in remFiles:
				remSize[words[8]] = long(words[4])
				timestamp = ' '.join(words[5:8])
				try:
					time = datetime.datetime.strptime(timestamp,'%b %d %Y')
				except ValueError:
					try:
						time = datetime.datetime.strptime("%s %d" % (timestamp,now.year),'%b %d %H:%M %Y')
					except ValueError:
						try:
							time = datetime.datetime.strptime("%s %d" % (timestamp,now.year-1),'%b %d %H:%M %Y')
						except ValueError:
							time = now
					if (
							(time.year == now.year and time.month > now.month) or
							(time.year == now.year and time.month == now.month and time.day > now.day)
					):
						time = time.replace(year=now.year-1)
				remTime[words[8]] = time
		
		# connect to source server
		self.log("connecting to FTP server %s ..." % remHost)
		ftp = ftplib.FTP(remHost)
		ftp.login() # anonymous
		self.log(" OK\n")
		
		# check remote file sizes and times
		self.log("identifying changed files ...")
		for remDir in remDirs:
			ftp.dir(remDir, ftpDirCB)
		self.log(" OK\n")
		
		# download files as needed
		self.logPush("downloading changed files ...\n")
		for locPath in sorted(remFiles.keys()):
			if remSize[locPath] == locSize[locPath] and remTime[locPath] <= locTime[locPath]:
				self.log("%s: up to date\n" % locPath)
			else:
				self.log("%s: downloading ..." % locPath)
				#TODO: download to temp file, then rename?
				with open(locPath, 'wb') as locFile:
					ftp.cwd(remFiles[locPath][0:remFiles[locPath].rfind('/')])
					ftp.retrbinary('RETR '+locPath, locFile.write)
				self.log(" OK\n")
			modTime = time.mktime(remTime[locPath].timetuple())
			os.utime(locPath, (modTime,modTime))
		
		# disconnect from source server
		try:
			ftp.quit()
		except Exception:
			ftp.close()
		self.logPop("... OK\n")
	#downloadFilesFromFTP()
	
	
	# remFiles={'filename.ext':'/path/on/remote/host/to/filename.ext',...}
	def downloadFilesFromHTTP(self, remHost, remFiles):
		# check local file sizes and times
		remSize = {}
		remTime = {}
		locSize = {}
		locTime = {}
		for locPath in remFiles:
			remSize[locPath] = None
			remTime[locPath] = None
			locSize[locPath] = None
			locTime[locPath] = None
			if os.path.exists(locPath):
				stat = os.stat(locPath)
				locSize[locPath] = long(stat.st_size)
				locTime[locPath] = datetime.datetime.fromtimestamp(stat.st_mtime)
		
		# check remote file sizes and times
		self.log("identifying changed files ...")
		for locPath in remFiles:
			try:
				http = httplib.HTTPConnection(remHost)
				http.request('HEAD', remFiles[locPath])
				response = http.getresponse()
			except IOError as e:
				self.log(" ERROR: %s" % e)
				return False
			
			content_length = response.getheader('content-length')
			if content_length:
				remSize[locPath] = long(content_length)
			
			last_modified = response.getheader('last-modified')
			if last_modified:
				try:
					remTime[locPath] = datetime.datetime.strptime(last_modified,'%a, %d %b %Y %H:%M:%S %Z')
				except ValueError:
					remTime[locPath] = datetime.datetime.now()
			
			http.close()
		self.log(" OK\n")
		
		# download files as needed
		self.logPush("downloading changed files ...\n")
		for locPath in sorted(remFiles.keys()):
			if remSize[locPath] and remSize[locPath] == locSize[locPath] and remTime[locPath] and remTime[locPath] <= locTime[locPath]:
				self.log("%s: up to date\n" % locPath)
			else:
				self.log("%s: downloading ..." % locPath)
				#TODO: download to temp file, then rename?
				with open(locPath, 'wb') as locFile:
					http = httplib.HTTPConnection(remHost)
					http.request('GET', remFiles[locPath])
					response = http.getresponse()
					while True:
						data = response.read()
						if not data:
							break
						locFile.write(data)
					http.close()
				self.log(" OK\n")
			if remTime[locPath]:
				modTime = time.mktime(remTime[locPath].timetuple())
				os.utime(locPath, (modTime,modTime))
		self.logPop("... OK\n")
	#downloadFilesFromHTTP()
	
	
#Source
