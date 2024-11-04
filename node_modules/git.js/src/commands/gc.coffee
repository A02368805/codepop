_ = require 'underscore'

# gc command plugin
module.exports = (git) ->
	return (opts) ->
		args = ['--quiet', transform(opts)]
		git.run('gc', args)

transform = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			switch k
				when "aggressive" then "--aggressive"
				when "auto" then "--auto"
				when "noprune" then "--no-prune"
				when "force" then "--force"
				else ''
	.filter _.identity
