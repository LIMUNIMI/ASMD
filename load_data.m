function load_data(varargin)
% Load data from `datasets.json` in this directory.
% - `instrument`:   a string representing the instrument that you want to filter
% - `ensemble`:     if loading songs which are composed for an ensemble of
%                   instrument (default `false`
% - `mixed`:        if returning the mixed track for ensemble song (default `true`)
% - `sources`:      if returning the source track for ensemble recording
%                   which provide it (default `false`)
% - `all`:          only valid if `sources` is `true`: if `true`, all
%                   sources (audio and ground-truth) are returned, if
%                   `false`, only the target instrument is returned
% - `composer`:     the surname of the composer to filter
% - `ground_truth`: a list of strings representing the type of
%                   ground-truths needed (logical AND among list elements)
% - `tmpfs`:        a string representing the directory where the returned ground
%                   truth files are copied - at least 100 MB of space is
%                   recquired. In linux, it is recommended to use a tmpfs
%                   filesystem. If free space is more than xx GB, than all
%                   ground-truth files are moved there, so that every
%                   compressed file is already in RAM.
%
% All parameters are optional and in name-value syntax

    % starting parser
    p = inputParser;
    addParameter(p, 'ensemble', false);
    addParameter(p, 'mixed', true);
    addParameter(p, 'sources', false);
    addParameter(p, 'composer', -1);
    addParameter(p, 'instrument', -1);
    addParameter(p, 'ground_truth', -1);
    addParameter(p, 'tmpfs', -1);
    parse(p, varargin{:});

    % opening json file
    data = jsondecode(fileread('datasets.json'));

    for i = 1:length(data.datasets)
        FLAG = true;
        dataset = data.datasets{i};

        % checking dataset-level filters
        if p.Results.ensemble ~= dataset.ensemble
            FLAG = false;
        end

        if p.Results.instrument ~= -1
            if ~contains(dataset.instruments, p.Results.instrument)
                FLAG = false;
            end
        end

        if p.Results.sources
            if dataset.sources.format ~= 'unknown'
                FLAG = false;
            end
        end

        if p.Results.ground_truth ~= -1
            for gt = p.Results.ground_truth
                if ~getfield(dataset.ground_truth, gt)
                    FLAG = false;
                    break;
                end
            end
        end

        if FLAG
            disp(dataset.name);
            for k = 1:length(dataset.songs)
                song = dataset.songs(k);
                % something

            end
        end
    end
