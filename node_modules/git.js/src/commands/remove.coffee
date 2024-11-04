_ = require 'underscore'

# remove command plugin
module.exports = (git) ->
	cmd = (files, opts) ->
		args = ['--quite', transform(opts)..., files...]
		git.run('rm', args)
	cmd.aliases = ['rm']
	cmd

transform = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			switch k
				when 'dryrun' then "--dry-run"
				when 'force' then "--force"
				else ''
	.filter _.identity
