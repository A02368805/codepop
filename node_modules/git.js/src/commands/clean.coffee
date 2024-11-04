_ = require 'underscore'

# clean command plugin
module.exports = (git) ->
	return (opts) ->
		args = ['--quiet', transform(opts)]
		git.run('clean', args)

transform = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			v = opts[k]
			switch k
				when "dryrun" then "--dry-run"
				when "force" then "--force"
				when "exclude" then "--exclude=#{v}"
				when "ignored" then "-X"
				when "noignore" then "-x"
				else ''
	.filter _.identity
