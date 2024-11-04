_ = require 'underscore'
_.str = require 'underscore.string'
Q = require 'q'
async = require 'async'

# log command plugin
module.exports = (git) ->
	return (opts) ->
		format = '--format=%H;%P;%an;%ae;%ad;%s'
		args = [format, '--date=iso', transform(opts)...]
		git.run('log', args).then(parse).then(extend(git))

transform = (opts) ->
	return [] unless opts
	# todo support more options like since, after, etc
	_.keys(opts)
	.map (k) ->
		v = opts[k]
		switch k
			when 'max' then "-n #{{v}}"
			else ''
	.filter _.identity

parse = (out) ->
	return [] unless out
	lines = _.str.lines(out)
	lines.map (l) ->
		p = l.split ';'
		id: p[0]
		parent: p[1]
		author:
			name: p[2]
			email: p[3]
		date: new Date(p[4])
		message: p[5]

extend = (git) ->
	(commits) ->
		list = commits.map (c) ->
			c.diff = -> diff(git, c)
			return c
		list.diffs = -> diffs(git, commits)
		list

# fetch diff for given commit
diff = (git, commit) ->
	git.show.diff(commit.id)

# fetch diffs for given commits
diffs = (git, commits) ->
	def = Q.defer()
	funcs = commits.map (c) -> diffAsyncFn(git, c)
	async.parallel funcs, (err, res) ->
		def.reject(err) if err
		def.resolve(res)
	def.promise

diffAsyncFn = (git, commit) ->
	(cb) ->
		diff(git, commit)
		.then (res) ->
			cb null, res
		.fail (err) ->
			cb err, null
