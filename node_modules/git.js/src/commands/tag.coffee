_ = require 'underscore'
_.str = require 'underscore.string'

# tag command plugin
module.exports = (git) ->
	cmd = (opts) ->
		git.run 'tag', transform(opts)

	# adds given tag
	cmd.add = (tag, opts) ->
		opts = {} unless opts
		how = '-a'
		how = '-s' if opts.signed
		how = "-u #{opts.key}" if opts.key
		git.run 'tag', [how, transform(opts)..., tag]

	# deletes given tags
	cmd.delete = (tags, opts) ->
		tags = [tags] if _.isString tags
		git.run 'tag', ['-d', transform(opts)..., tags...]

	# verifies signature of given tags
	cmd.verify = (tags, opts) ->
		tags = [tags] if _.isString tags
		git.run 'tag', ['-v', transform(opts)..., tags...]

	# lists tags by given pattern
	cmd.list = (pattern, opts) ->
		git.run 'tag', ['-l', pattern, transform(opts)...]

	cmd

transform = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			v = opts[k]
			switch k
				when 'force' then "--force"
				when 'message' then "-m #{_.str.quote(v, '\'')}"
				else ''
	.filter _.identity
