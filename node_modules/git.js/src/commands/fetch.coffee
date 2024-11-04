_ = require 'underscore'

# fetch command plugin
module.exports = (git) ->
	return (repository, opts) ->
		args = ['--quiet', transform(opts)..., repository]
		git.run('clone', args)

transform = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			v = opts[k]
			switch k
				when 'all' then "--all"
				when 'append' then "--append"
				when 'depth' then "--depth=#{v}"
				when 'dryrun' then "--dry-run"
				when 'force' then "--force"
				when 'keep' then "--keep"
				when 'notags' then "--no-tags"
				when 'recurseSubmodules' then "--recurse-submodules=#{v}"
				else ''
	.filter _.identity
