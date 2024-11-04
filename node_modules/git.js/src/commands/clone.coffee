_ = require 'underscore'

# clone command plugin
module.exports = (git) ->
	return (url, directory, opts) ->
		args = ['--quiet', transform(opts)..., url]
		args.push directory if directory
		git.run('clone', args)

transform = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			v = opts[k]
			switch k
				when 'nohardlinks' then "--no-hardlinks"
				when 'shared' then "--shared"
				when 'nocheckout' then "--no-checkout"
				when 'bare' then "--bare"
				when 'mirror' then "--mirror"
				when "branch" then "--branch #{v}"
				when "recursive" then "--recursive"
				else ''
	.filter _.identity
