_ = require 'underscore'
_.str = require 'underscore.string'

# push command plugin
module.exports = (git) ->
	return (opts) ->
		args = ['--porcelain', transform(opts)...]
		git.run('push', args).then(parse)

transform = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			switch k
				when 'dryrun' then "--dry-run"
				when 'all' then "--all"
				when 'force' then "--force"
				else ''
	.filter _.identity

parse = (out) ->
	return [] unless out
	lines = _.str.lines(out)
	# todo parse refs
	lines
