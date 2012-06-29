import loki_source
import itertools

class Source_ucsc_ecr(loki_source.Source):
	"""
	A class to load the pairwise alignments between species as ECRs from the 
	UCSC inter-species alignments
	"""

	
	_remhost = "hgdownload.cse.ucsc.edu"
	_remPath = "goldenPath/hg19/phastCons46way/"
	_comparisons = {"vertebrate" : "", "placentalMammals" : "placental." , "primates" : "primates." }
	_min_sz = 100
	_min_pct = 0.7
	_max_gap = 50
	
	
	def download(self, options):
		"""
		Download the files
		"""
		self._chr_list = ('1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20','21','22','X','Y')
		file_dict = dict(((sp + ".chr" + ch + ".phastCons.txt.gz", self._remPath + sp + "/chr" + ch + ".phastCons46way." + v + "wigFix.gz") for (sp, v) in self._comparisons.iteritems() for ch in self._chr_list))
		file_dict.update(dict(((sp + ".chrMT.phastCons.txt.gz", self._remPath + sp + "/chrM.phastCons46way." + v + "wigFix.gz") for (sp, v) in self._comparisons.iteritems())))
	
		self.downloadFilesFromFTP(self._remhost,file_dict)

	def update(self, options):
		"""
		Load the data from all of the files
		"""
		self.log("deleting old records from the database ...")
		self.deleteAll()
		self.log(" OK\n")
		
		# Add a namespace
		ecr_ns = self.addNamespace("ucsc_ecr")
		
		# Add a type of "ecr"
		ecr_typeid = self.addType("ecr")
		
		# Add a type of "ecr_group"
		ecr_group_typeid = self.addType("ecr_group")
		
		# Make sure the 'n/a' ldprofile exists
		ecr_ldprofile_id = self.addLDProfile('n/a', 'no LD adjustment', None)
		
		
		
		for sp in self._comparisons:
			self.logPush("processing ECRs for " + sp + " ...")
			desc = "ECRs for " + sp
			label = "ecr_" + sp
			
			# Add the group for this species (or comparison)
			ecr_gid = self.addTypedGroups(ecr_group_typeid, [(label, desc)])[0]
			self.addGroupNamespacedNames(ecr_ns, [(ecr_gid, label)])
						
			for ch in self._chr_list + ("MT",):
				ch_id = self._loki.chr_num[ch]
				self.log("processing Chromosome " + ch + " ...")
				f = self.zfile(sp + ".chr" + ch + ".phastCons.txt.gz")
				regions = [r for r in self.getRegions(f)]
											
				# Add the region itself
				reg_ids = self.addTypedBiopolymers(ecr_typeid, ((self.getRegionName(sp, ch, r), '') for r in regions))
				# Add the name of the region
				self.addBiopolymerNamespacedNames(ecr_ns, zip(reg_ids, (self.getRegionName(sp, ch, r) for r in regions)))
				# Add the region Boundaries
				# This gives a generator that yields [(region_id, (chrom_id, start, stop)) ... ]
				region_bound_gen = zip(((i,) for i in reg_ids), ((ch_id, r[0], r[1]) for r in regions))
				self.addBiopolymerLDProfileRegions(ecr_ldprofile_id, (tuple(itertools.chain(*c)) for c in region_bound_gen))			

				#Add the region to the group
				self.addGroupBiopolymers(((ecr_gid, r_id) for r_id in reg_ids))
				
				self.log("OK (" + str(len(regions)) + " regions found)\n")
			
			self.logPop("... OK\n")

				
				
	def getRegionName(self, species, ch, region):
		"""
		Returns a string representation of the name
		"""
		return species + ":chr" + ch + ":" + str(region[0]) + "-" + str(region[1])
				
	
	def getRegions(self, f):
		"""
		Yields the regions that meets the thresholds with a given maximum gap
		"""
		running_sum = 0
		n_pos = 0
		curr_gap = 0
		curr_pos = 1
		curr_start = 1
		curr_end = 0
		step = 1
		
		line = f.next()
		
		
		for l in f:
			try:
				p = float(l)
				if p >= self._min_pct:
					#If this is the 1st time we crossed the threshold, start the counters
					if curr_gap != 0 and running_sum / float(n_pos) < self._min_pct:
						if curr_end- curr_start >= self._min_sz:
							yield (curr_start, curr_end)
						
						# Restart the region tracking
						running_sum = 0
						n_pos = 0
					
					if n_pos == 0:
						curr_start = curr_pos
											
					curr_end = curr_pos
					running_sum += p
					n_pos += 1
					curr_gap = 0
				# If this is true, we're searching a gap				
				elif n_pos != 0:
					#print curr_gap, curr_end - curr_start
					# If we are in an acceptable gap, don't add on to the end
					if curr_gap < self._max_gap:
						running_sum += p
						n_pos += 1
						curr_gap += 1
					else:
						# If it's big enough, add it (we ran off the end of the gap)
						if curr_end - curr_start > self._min_sz:
							yield (curr_start, curr_end)
						n_pos = 0
						curr_start = 0
						curr_end = 0
						running_sum = 0
						curr_gap = 0
				# otherwise, just keep on trucking		
				curr_pos += step
			except ValueError:
				# At this point, we have a format line
				d = dict((v.split('=',2) for v in l.split() if v.find('=') != -1))
				
				# If this is moving us to a different place, we have to restart,
				# o/w just keep on trucking
				if int(d['start']) != curr_pos or int(d['step']) != step:
					
					if curr_end - curr_start > self._min_sz and running_sum / float(n_pos) >= self._min_pct and curr_gap < self._max_gap:
						yield (curr_start, curr_end)
	
	
					running_sum = 0
					n_pos = 0
					curr_gap = 0
					curr_pos = int(d['start'])
					curr_start = int(d['start'])
					step = int(d['step'])
					curr_end = 0
				
		
		# Check on the last region...
		if curr_end - curr_start > self._min_sz and running_sum / float(n_pos) >= self._min_pct and curr_gap < self._max_gap:
			 yield (curr_start, curr_end)
						

				
				
				
				
				
			
		
		
	
	
