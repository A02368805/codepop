_ = require 'underscore'

# add command plugin
module.exports = (git) ->
	return (files, opts) ->
		args = [transform(opts)..., files...]
		git.run('add', args)

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
