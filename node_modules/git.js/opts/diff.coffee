_ = require 'underscore'

# common diff options
module.exports = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			v = opts[k]
			switch k
				when 'n' then "--unified=#{v}"
				when 'minimal' then "--minimal"
				when 'patience' then "--patience"
				when 'histogram' then "--histogram"
				when 'algorithm' then "--diff-algorithm=#{v}"
				when 'summary' then "--summary"
				else ''
	.filter _.identity
