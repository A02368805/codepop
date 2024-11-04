_ = require 'underscore'

# pull command plugin
module.exports = (git) ->
	return (opts) ->
		args = ['--quiet', transform(opts)...]
		git.run('pull', args)

transform = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			switch k
				# fetch all remotes.
				when 'all' then "--all"
				when 'force' then "--force"
				when 'keep' then "--keep"
				when 'update' then "-u"
				else ''
	.filter _.identity
